"""Audio upload and retention endpoints (M5).

The API never receives audio bytes. The client uploads directly to object
storage with a short-lived key, and this service only records that an object
exists and when it must be destroyed.

Every write passes the consent gate. Every write stamps a TTL. There is no code
path that stores audio without both.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.repositories.learners import AudioRepository, ConsentRepository
from app.security.auth import CurrentUser
from app.security.consent import PURPOSES, ConsentError
from app.security.retention import AudioObject, RetentionReason, expiry_for

router = APIRouter(prefix="/audio", tags=["audio"])

Session = Annotated[AsyncSession, Depends(get_session)]


class UploadRequest(BaseModel):
    session_id: str
    block_id: str
    reason: Literal["processing", "learner_review", "research_corpus"] = "processing"
    duration_seconds: float = Field(ge=0, le=600)


class UploadTicket(BaseModel):
    key: str
    upload_url: str
    expires_at: datetime | None
    reason: str
    #: Shown to the learner verbatim. They are entitled to know how long their
    #: voice is kept, in words, at the moment they record it.
    retention_notice: str


class ConsentRequest(BaseModel):
    purpose: str
    granted: bool
    guardian_user_id: str | None = None


class ConsentStatus(BaseModel):
    user_id: str
    granted: list[str]
    available: list[str]


class PurgeSummary(BaseModel):
    deleted: int
    remaining: int


@router.post("/upload-url", response_model=UploadTicket, summary="Get an upload ticket")
async def request_upload(
    principal: CurrentUser,
    session: Session,
    request: Annotated[UploadRequest, Body()],
) -> UploadTicket:
    reason = RetentionReason(request.reason)
    consents = ConsentRepository(session)

    try:
        # The processing consent is always required; a reason beyond processing
        # requires its own, separate grant.
        if not await consents.has_consent(principal.user_id, "speech_processing"):
            raise ConsentError(principal.user_id, "speech_processing")
        if reason is not RetentionReason.PROCESSING:
            purpose = _consent_for(reason)
            if not await consents.has_consent(principal.user_id, purpose):
                raise ConsentError(principal.user_id, purpose)
    except ConsentError as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "error": "consent_required",
                "purpose": error.purpose,
                "message": "We need your permission before we can record this.",
            },
        ) from error

    now = datetime.now(timezone.utc)
    key = f"audio/{now:%Y/%m/%d}/{request.session_id}/{uuid4().hex}.wav"
    expires_at = expiry_for(reason, now)

    await AudioRepository(session).put(
        AudioObject(
            key=key,
            user_id=principal.user_id,
            reason=reason,
            created_at=now,
            expires_at=expires_at,
        )
    )

    return UploadTicket(
        key=key,
        # A presigned URL from object storage lands in M17; the shape is fixed
        # now so the client is not rewritten when it does.
        upload_url=f"{get_settings().speech_service_url}/upload/{key}",
        expires_at=expires_at,
        reason=reason.value,
        retention_notice=_notice(reason),
    )


@router.post("/consent", response_model=ConsentStatus, summary="Grant or revoke consent")
async def set_consent(
    principal: CurrentUser,
    session: Session,
    request: Annotated[ConsentRequest, Body()],
) -> ConsentStatus:
    if request.purpose not in PURPOSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown purpose '{request.purpose}'")

    consents = ConsentRepository(session)
    await consents.record(
        principal.user_id, request.purpose, request.granted, request.guardian_user_id
    )

    if not request.granted:
        # Revocation deletes, immediately. Consent that can be withdrawn without
        # the data going with it is not consent, it is a preference.
        audio = AudioRepository(session)
        if request.purpose in _REASON_FOR_CONSENT:
            await audio.purge_for_user(principal.user_id, _REASON_FOR_CONSENT[request.purpose])
        elif request.purpose == "speech_processing":
            await audio.purge_for_user(principal.user_id)

    return await consent_status(principal, session)


@router.get("/consent", response_model=ConsentStatus, summary="Current consents")
async def consent_status(principal: CurrentUser, session: Session) -> ConsentStatus:
    """No user id in the path. A learner may only read their own consents."""
    granted = await ConsentRepository(session).granted(principal.user_id)
    return ConsentStatus(
        user_id=principal.user_id,
        granted=sorted(granted),
        available=sorted(PURPOSES),
    )


class StoredRecording(BaseModel):
    key: str
    reason: str
    created_at: datetime
    expires_at: datetime | None


@router.get("/mine", response_model=list[StoredRecording], summary="What recordings we hold")
async def my_recordings(principal: CurrentUser, session: Session) -> list[StoredRecording]:
    """Every recording of this learner's voice that still exists, and when each
    one disappears.

    A learner is entitled to know what we hold without asking anyone. A promise
    in a policy document that cannot be checked is not transparency, and voice
    is the most sensitive thing this product stores.
    """
    objects = await AudioRepository(session).list_for_user(principal.user_id)
    return [
        StoredRecording(
            key=obj.key,
            reason=obj.reason.value,
            created_at=obj.created_at,
            expires_at=obj.expires_at,
        )
        for obj in objects
    ]


@router.post("/purge", response_model=PurgeSummary, summary="Run the retention purge")
async def run_purge(session: Session) -> PurgeSummary:
    """Delete everything past its TTL.

    Exposed so the scheduled job and the tests exercise the same code path. In
    production this is called by a cron worker, not by a client.
    """
    deleted = await AudioRepository(session).purge_expired()
    return PurgeSummary(deleted=len(deleted), remaining=0)


@router.delete("/me", response_model=PurgeSummary, summary="Erase my audio")
async def erase_mine(principal: CurrentUser, session: Session) -> PurgeSummary:
    audio = AudioRepository(session)
    deleted = await audio.purge_for_user(principal.user_id)
    remaining = len(await audio.list_for_user(principal.user_id))
    return PurgeSummary(deleted=len(deleted), remaining=remaining)


_REASON_FOR_CONSENT = {
    "store_audio_for_review": RetentionReason.LEARNER_REVIEW,
    "research_corpus": RetentionReason.RESEARCH_CORPUS,
}


def _consent_for(reason: RetentionReason) -> str:
    for purpose, mapped in _REASON_FOR_CONSENT.items():
        if mapped is reason:
            return purpose
    return "speech_processing"


def _notice(reason: RetentionReason) -> str:
    """Plain language. A learner should not have to read a policy to know this."""
    if reason is RetentionReason.PROCESSING:
        return "Your recording is deleted within 24 hours. We keep only the scores."
    if reason is RetentionReason.LEARNER_REVIEW:
        return "Your recording is kept for 30 days so you and your trainer can listen back."
    return (
        "Your recording is kept to help improve speech technology for disabled people. "
        "You can withdraw at any time and it will be deleted."
    )

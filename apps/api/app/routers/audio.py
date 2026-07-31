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

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security.consent import (
    PURPOSES,
    ConsentError,
    InMemoryConsentLedger,
    require_consent,
)
from app.security.retention import (
    AudioObject,
    InMemoryAudioStore,
    RetentionReason,
    expiry_for,
    purge_expired,
    purge_for_user,
)

router = APIRouter(prefix="/audio", tags=["audio"])

# TEMPORARY: replaced by Supabase storage and the Postgres ledger in M17.
_store = InMemoryAudioStore()
_ledger = InMemoryConsentLedger()


class UploadRequest(BaseModel):
    user_id: str
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
    user_id: str
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
async def request_upload(request: Annotated[UploadRequest, Body()]) -> UploadTicket:
    reason = RetentionReason(request.reason)

    try:
        # The processing consent is always required; a reason beyond processing
        # requires its own, separate grant.
        require_consent(_ledger, request.user_id, "speech_processing")
        if reason is not RetentionReason.PROCESSING:
            require_consent(_ledger, request.user_id, _consent_for(reason))
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

    _store.put(
        AudioObject(
            key=key,
            user_id=request.user_id,
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
async def set_consent(request: Annotated[ConsentRequest, Body()]) -> ConsentStatus:
    if request.purpose not in PURPOSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown purpose '{request.purpose}'")

    if request.granted:
        _ledger.grant(request.user_id, request.purpose, request.guardian_user_id)
    else:
        _ledger.revoke(request.user_id, request.purpose)

        # Revocation deletes, immediately. Consent that can be withdrawn without
        # the data going with it is not consent, it is a preference.
        if request.purpose in _REASON_FOR_CONSENT:
            purge_for_user(_store, request.user_id, _REASON_FOR_CONSENT[request.purpose])
        elif request.purpose == "speech_processing":
            purge_for_user(_store, request.user_id)

    return await consent_status(request.user_id)


@router.get("/consent/{user_id}", response_model=ConsentStatus, summary="Current consents")
async def consent_status(user_id: str) -> ConsentStatus:
    return ConsentStatus(
        user_id=user_id,
        granted=sorted(p for p in PURPOSES if _ledger.has_consent(user_id, p)),
        available=sorted(PURPOSES),
    )


@router.post("/purge", response_model=PurgeSummary, summary="Run the retention purge")
async def run_purge() -> PurgeSummary:
    """Delete everything past its TTL.

    Exposed so the scheduled job and the tests exercise the same code path. In
    production this is called by a cron worker, not by a client.
    """
    result = purge_expired(_store)
    return PurgeSummary(deleted=result.count, remaining=result.remaining)


@router.delete("/user/{user_id}", response_model=PurgeSummary, summary="Erase a learner's audio")
async def erase_user(user_id: str) -> PurgeSummary:
    result = purge_for_user(_store, user_id)
    return PurgeSummary(deleted=result.count, remaining=result.remaining)


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

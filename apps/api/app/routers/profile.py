"""The Communication Ability Profile (M1).

The single most important object in the system. Everything downstream — the
Modality Router, the session builder, the PPI weighting, every dashboard — reads
it. Until now it was a hard-coded demo persona, which meant the whole modality
architecture was serving a fixture rather than a person.

TWO RULES
---------
**Versioned, never updated.** Each save writes a new row. Progress data records
the version it was collected under, so a learner who moves from speech to
symbols does not have their earlier scores silently reinterpreted — and a
trainer can see that a change in scores followed a change in profile.

**Validated against the contract, not trusted.** The client is not the authority
on what a valid profile is; `packages/contracts` is. A profile that fails
validation is rejected here rather than stored and discovered later by a
renderer that cannot cope with it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import CommunicationAbilityProfile
from app.db.session import get_session
from app.repositories.learners import ProfileRepository
from app.security.auth import CurrentUser

router = APIRouter(prefix="/profile", tags=["profile"])

Session = Annotated[AsyncSession, Depends(get_session)]

#: What a learner gets before they have told us anything.
#:
#: Chosen to be usable by the widest possible range of people rather than to be
#: neutral: captions and audio together, standard text, every input mode
#: accepted. Onboarding NARROWS this. It must never be silently widened at
#: runtime, because widening means assuming a capability nobody confirmed.
STARTING_PROFILE: dict = {
    "version": 1,
    "input_channels": ["text", "speech", "aac", "switch"],
    "output_channels": ["captioned_text", "audio"],
    "text_complexity": "standard",
    "speech_status": "undeclared",
    "primary_language": "en-IN",
    "presentation": {
        "audio_rate": 1.0,
        "contrast_theme": "standard",
        "colour_scheme": "system",
        "motion_reduced": False,
        "target_size_px": 44,
        "captions_enabled": True,
        "one_step_per_screen": False,
    },
}


@router.get("", summary="My profile")
async def get_profile(principal: CurrentUser, session: Session) -> dict:
    """The current profile, or the starting one if onboarding has not run.

    Returns a usable profile either way. A client that has to handle "no profile
    yet" as a special case will get it wrong somewhere, and the failure mode is
    a learner facing a screen in a modality they cannot use.
    """
    stored = await ProfileRepository(session).current(principal.user_id)

    if stored is None:
        return {
            **STARTING_PROFILE,
            "user_id": principal.user_id,
            "onboarding_complete": False,
        }

    return {**stored, "onboarding_complete": True}


@router.put("", summary="Save my profile")
async def save_profile(
    principal: CurrentUser,
    session: Session,
    profile: Annotated[dict, Body()],
) -> dict:
    """Write the next version.

    The learner may save partway through onboarding — the four-door screen alone
    is enough to render the rest of the flow — so this accepts a profile that is
    valid but not yet complete.
    """
    candidate = {
        **profile,
        "user_id": principal.user_id,
        # Version is assigned by the repository. Accepting it from the client
        # would let a stale tab overwrite a newer profile.
        "version": 1,
    }

    try:
        CommunicationAbilityProfile.model_validate(candidate)
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_profile",
                "message": "We could not save those settings. Please try again.",
                "problems": [
                    {"field": ".".join(str(p) for p in e["loc"]), "issue": e["msg"]}
                    for e in error.errors()[:5]
                ],
            },
        ) from error

    stored = await ProfileRepository(session).save(principal.user_id, candidate)
    return {**stored, "onboarding_complete": True}


@router.get("/history", summary="How my profile has changed")
async def profile_history(principal: CurrentUser, session: Session) -> list[dict]:
    """Every version, oldest first.

    A learner is entitled to see what we believe about how they communicate, and
    a trainer needs it to tell a change in ability from a change in settings.
    """
    return await ProfileRepository(session).history(principal.user_id)

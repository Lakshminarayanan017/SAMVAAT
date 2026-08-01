"""Sessions.

Guest-first. A learner can start with no account at all, because someone
deciding whether to trust us should be able to practise saying "good morning"
before handing over an email — and for a disabled learner weighing up who gets
to know about their disability, that is not a small thing.

Signing up later upgrades the same row, so a week of practice is not the price
of creating an account.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.learners import ProfileRepository, UserRepository
from app.security.auth import CurrentUser, issue_token, new_user_id

router = APIRouter(prefix="/auth", tags=["auth"])

Session = Annotated[AsyncSession, Depends(get_session)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    is_guest: bool
    #: Lets the client show the right tabs. NOT a permission — the API refuses
    #: trainer routes on the token's claim regardless of what the client renders.
    role: str = "learner"
    #: True when this learner has never completed onboarding, so the client
    #: knows to show the four-door screen rather than the practice loop.
    needs_onboarding: bool = True


class UpgradeRequest(BaseModel):
    email: EmailStr = Field(description="Where a magic link would be sent, once M17 adds one.")


@router.post("/guest", response_model=TokenResponse, summary="Start without an account")
async def guest(session: Session) -> TokenResponse:
    users = UserRepository(session)
    user_id = new_user_id(guest=True)
    await users.create(user_id, is_guest=True)

    return TokenResponse(
        access_token=issue_token(user_id, is_guest=True),
        user_id=user_id,
        is_guest=True,
        role="learner",
        needs_onboarding=True,
    )


@router.get("/me", response_model=TokenResponse, summary="Who am I, and refresh my session")
async def me(principal: CurrentUser, session: Session) -> TokenResponse:
    users = UserRepository(session)
    user = await users.get(principal.user_id)

    if user is None:
        # A validly signed token for a user that no longer exists — the learner
        # exercised erasure. Treat it as signed out, never as an error.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthenticated", "message": "Please sign in to continue."},
        )

    await users.touch(principal.user_id)
    profile = await ProfileRepository(session).current(principal.user_id)

    return TokenResponse(
        access_token=issue_token(user.id, role=user.role, is_guest=user.is_guest),
        user_id=user.id,
        is_guest=user.is_guest,
        role=user.role,
        needs_onboarding=profile is None,
    )


@router.post("/upgrade", response_model=TokenResponse, summary="Turn a guest into an account")
async def upgrade(
    principal: CurrentUser, session: Session, request: Annotated[UpgradeRequest, Body()]
) -> TokenResponse:
    users = UserRepository(session)

    existing = await users.get_by_email(request.email)
    if existing and existing.id != principal.user_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "error": "email_in_use",
                "message": "That email is already used. Sign in with it instead.",
            },
        )

    user = await users.upgrade_guest(principal.user_id, request.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such user")

    profile = await ProfileRepository(session).current(user.id)

    return TokenResponse(
        access_token=issue_token(user.id, role=user.role, is_guest=False),
        user_id=user.id,
        is_guest=False,
        role=user.role,
        needs_onboarding=profile is None,
    )


@router.delete("/me", summary="Erase everything about me")
async def erase(principal: CurrentUser, session: Session) -> dict:
    """Data-subject erasure, self-service and immediate.

    A right that requires emailing somebody is not a right a disabled learner
    can reliably exercise. Every table is cleared here rather than relying on
    cascades, so each repository's deletion is independently testable and no
    table can be forgotten because its foreign key happened to be nullable.

    That last sentence used to be aspirational. Three tables — the profile, the
    consent ledger and the trainer link — were missing from this list and
    survived erasure, because the user row is removed with a Core `delete()`
    (which does not run ORM cascades) and SQLite ignores foreign keys unless
    `PRAGMA foreign_keys=ON`. The trainer link carries the learner's real name.

    `tests/test_erasure_completeness.py` now walks the schema and fails on any
    table that still names the learner, so this list cannot silently fall
    behind the model again.
    """
    from app.repositories.learners import (
        AudioRepository,
        AuditRepository,
        CardRepository,
        ConsentRepository,
        ConversationRepository,
        ProfileRepository,
    )
    from app.repositories.trainers import TrainerRepository

    user_id = principal.user_id

    await CardRepository(session).delete_for_user(user_id)
    await ConversationRepository(session).delete_for_user(user_id)
    await AudioRepository(session).purge_for_user(user_id)
    await AuditRepository(session).delete_for_user(user_id)
    await ProfileRepository(session).delete_for_user(user_id)
    await ConsentRepository(session).delete_for_user(user_id)
    await TrainerRepository(session).delete_for_learner(user_id)
    await UserRepository(session).delete(user_id)

    return {
        "erased": True,
        "message": "Everything about you has been deleted. Thank you for practising with us.",
    }

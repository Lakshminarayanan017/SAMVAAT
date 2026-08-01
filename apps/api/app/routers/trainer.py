"""The trainer dashboard (M14).

What turns this from a consumer app into something an institution will deploy —
and the surface that makes Ethics E5 real rather than aspirational.

TWO GATES ON EVERY READ
-----------------------
1. **Role.** `require_trainer` — a learner token cannot reach any of this.
2. **Consent.** The learner's own `trainer_visibility` grant, checked per
   learner at the query layer.

A trainer with a caseload of thirty sees data for those who chose to share, and
"not shared yet" for the rest. Not an error, not an empty row — a plain
statement that the learner has not agreed, which is a fact the trainer needs and
is entitled to know.

ETHICS E5
---------
`POST /trainer/override` records a trainer's correction ONTO the audit row
rather than replacing the AI's score. "The AI said X, the trainer said Y,
because Z" is the record that makes the AI answerable; overwriting would destroy
exactly the evidence that matters.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.learners import ProfileRepository
from app.repositories.trainers import TrainerRepository
from app.security.auth import TrainerUser

router = APIRouter(prefix="/trainer", tags=["trainer"])

Session = Annotated[AsyncSession, Depends(get_session)]


class CohortMemberOut(BaseModel):
    learner_user_id: str
    display_name: str
    #: False means the learner has not granted `trainer_visibility`. Every
    #: metric below is then null, because we do not guess.
    shared: bool
    cards_started: int | None = None
    cards_due: int | None = None
    lapses: int | None = None
    interviews_completed: int | None = None
    last_active_at: str | None = None
    is_active: bool = False


class LinkRequest(BaseModel):
    learner_user_id: str
    display_name: str = Field(default="", max_length=120)
    institution_id: str | None = None


class OverrideRequest(BaseModel):
    audit_id: str
    #: What the trainer says instead.
    override: str = Field(max_length=2000)
    #: Why. Required, and not merely for the record: a specialist forced to
    #: articulate a disagreement usually sharpens it, and this text is the
    #: training signal for improving the rubric.
    reason: str = Field(min_length=3, max_length=2000)


@router.get("/cohort", response_model=list[CohortMemberOut], summary="My caseload")
async def cohort(trainer: TrainerUser, session: Session) -> list[CohortMemberOut]:
    members = await TrainerRepository(session).cohort(trainer.user_id)

    return [
        CohortMemberOut(
            learner_user_id=member.learner_user_id,
            display_name=member.display_name,
            shared=member.shared,
            cards_started=member.cards_started,
            cards_due=member.cards_due,
            lapses=member.lapses,
            interviews_completed=member.interviews_completed,
            last_active_at=member.last_active_at.isoformat() if member.last_active_at else None,
            is_active=member.is_active,
        )
        for member in members
    ]


@router.post("/link", summary="Add a learner to my caseload")
async def link(
    trainer: TrainerUser, session: Session, request: Annotated[LinkRequest, Body()]
) -> dict:
    """An administrative act, not a grant of access.

    Linking makes a learner appear on the caseload. It does NOT reveal their
    data — that needs their own consent, which they give and withdraw.
    """
    await TrainerRepository(session).link(
        trainer.user_id, request.learner_user_id, request.display_name, request.institution_id
    )
    return {
        "linked": True,
        "message": (
            "Added. You will see their progress once they choose to share it with you."
        ),
    }


@router.delete("/link/{learner_user_id}", summary="Remove a learner from my caseload")
async def unlink(trainer: TrainerUser, session: Session, learner_user_id: str) -> dict:
    await TrainerRepository(session).unlink(trainer.user_id, learner_user_id)
    return {"linked": False}


@router.get("/learner/{learner_user_id}", summary="One learner in detail")
async def learner_detail(
    trainer: TrainerUser, session: Session, learner_user_id: str
) -> dict:
    trainers = TrainerRepository(session)

    if not await trainers.is_linked(trainer.user_id, learner_user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such learner on your caseload")

    if not await trainers.may_view(trainer.user_id, learner_user_id):
        # 200, not 403. The trainer legitimately has this person on their
        # caseload; there is simply nothing to show. An error would read as a
        # fault when it is a choice the learner made.
        return {
            "learner_user_id": learner_user_id,
            "shared": False,
            "message": (
                "This learner has not chosen to share their progress with you yet. "
                "They can turn that on themselves at any time."
            ),
        }

    profile = await ProfileRepository(session).current(learner_user_id)
    members = await trainers.cohort(trainer.user_id)
    member = next((m for m in members if m.learner_user_id == learner_user_id), None)

    return {
        "learner_user_id": learner_user_id,
        "shared": True,
        # So a trainer can see the learner's scores changed because their
        # profile changed, not because they got worse.
        "profile": profile,
        "summary": {
            "cards_started": member.cards_started if member else 0,
            "cards_due": member.cards_due if member else 0,
            "lapses": member.lapses if member else 0,
            "interviews_completed": member.interviews_completed if member else 0,
        },
    }


@router.post("/override", summary="Override an AI score")
async def override(
    trainer: TrainerUser, session: Session, request: Annotated[OverrideRequest, Body()]
) -> dict:
    """Ethics E5, made real.

    AI is a co-pilot to the special educator, never a replacement.
    """
    row = await TrainerRepository(session).override_score(
        request.audit_id, trainer.user_id, request.override, request.reason
    )

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such score")

    return {
        "audit_id": row.id,
        "overridden": True,
        "override": row.trainer_override,
        "reason": row.override_reason,
        # The AI's original assessment is still here. That is the point.
        "original_rubric_version": row.rubric_version,
        "original_scored_dimensions": row.scored_dimensions,
    }


@router.get("/agreement", summary="How often I disagree with the AI")
async def agreement(trainer: TrainerUser, session: Session) -> dict:
    """The most honest quality metric we have.

    A rising override rate means the model is drifting away from what a
    specialist would say, and it should be read before any improvement in the
    scores themselves.
    """
    stats = await TrainerRepository(session).override_rate(trainer.user_id)
    return {
        **stats,
        "target_agreement": 0.85,
        "note": (
            "Below 85% agreement, the scoring needs work — not the trainers."
        ),
    }

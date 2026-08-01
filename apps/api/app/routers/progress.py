"""A learner's own progress (M12, M13, and the learner half of M14).

Everything here is about one learner, measured against themselves. There is no
argument, field or query in this router by which another learner's performance
could enter — which is ADR-0003 applied to motivation as strictly as to scoring.

WHAT THIS DELIBERATELY DOES NOT RETURN
--------------------------------------
No percentile. No cohort average. No "you are ahead of / behind" anything. A
disabled learner has spent a lifetime being measured against a norm they were
never going to meet; the whole product exists to stop doing that.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.learning.content import get_block, load_blocks
from app.learning.motivation import (
    BADGES_BY_ID,
    Attempt,
    LearnerProgress,
    PracticeRecord,
    award_xp,
    newly_earned,
)
from app.learning.recommend import Candidate, LearnerContext, recommend
from app.models.tables import CardRow, ConversationRow
from app.repositories.learners import ProfileRepository
from app.security.auth import CurrentUser

router = APIRouter(prefix="/progress", tags=["progress"])

Session = Annotated[AsyncSession, Depends(get_session)]

#: A phrase counts as reliable once it has survived this long between reviews.
#: Not "answered right once" — that is recall, not retention.
MASTERY_STABILITY_DAYS = 21.0


class BadgeOut(BaseModel):
    id: str
    family: str
    label: str
    earned_message: str


class ProgressOut(BaseModel):
    #: Total effort, not total correctness.
    xp: int
    days_practised: int
    current_run: int
    longest_run: int
    #: Written for the learner. Never mentions a broken run.
    summary: str
    phrases_started: int
    phrases_reliable: int
    interviews_completed: int
    badges: list[BadgeOut]


class RecommendationOut(BaseModel):
    block_id: str
    canonical_text: str
    #: Shown verbatim. The client never re-derives this, so there is one
    #: wording and it is testable.
    explanation: str
    reason: str


@router.get("", response_model=ProgressOut, summary="How I am doing")
async def my_progress(principal: CurrentUser, session: Session) -> ProgressOut:
    cards = list(
        (
            await session.execute(select(CardRow).where(CardRow.user_id == principal.user_id))
        ).scalars()
    )

    interviews = len(
        list(
            (
                await session.execute(
                    select(ConversationRow).where(
                        ConversationRow.user_id == principal.user_id,
                        ConversationRow.kind == "interview",
                        ConversationRow.finished.is_(True),
                    )
                )
            ).scalars()
        )
    )

    # Distinct days on which anything was reviewed. Rebuilt from the cards
    # rather than stored, so it cannot drift from what actually happened.
    practised_days = sorted(
        {card.last_reviewed_at.date() for card in cards if card.last_reviewed_at}
    )

    record = PracticeRecord()
    for day in practised_days:
        record = record.register(day)

    # XP is recomputed from history for the same reason: a stored counter that
    # disagrees with the record is a counter nobody can defend.
    xp = 0
    for card in cards:
        block = get_block(card.block_id)
        difficulty = block["difficulty"] if block else 1
        xp += card.reps * award_xp(
            Attempt(difficulty=difficulty, is_new=False, had_lapsed=card.lapses > 0)
        )

    reliable = sum(1 for card in cards if card.stability >= MASTERY_STABILITY_DAYS)

    progress = LearnerProgress(
        days_practised=record.days_practised,
        returned_after_break=record.returned_after_break,
        phrases_mastered=reliable,
        interviews_completed=interviews,
        retried_after_a_lapse=any(card.lapses > 0 and card.reps > card.lapses for card in cards),
        earned=set(),
    )

    return ProgressOut(
        xp=xp,
        days_practised=record.days_practised,
        current_run=record.current_run,
        longest_run=record.longest_run,
        summary=record.summary(),
        phrases_started=len(cards),
        phrases_reliable=reliable,
        interviews_completed=interviews,
        badges=[
            BadgeOut(
                id=badge.id,
                family=badge.family.value,
                label=badge.label,
                earned_message=badge.earned_message,
            )
            for badge in newly_earned(progress)
        ],
    )


@router.get("/badges", response_model=list[BadgeOut], summary="Every badge there is")
async def all_badges() -> list[BadgeOut]:
    """The full set, so a learner can see what exists rather than only what
    they have. Hidden goals are a dark pattern; visible ones are a map."""
    return [
        BadgeOut(
            id=badge.id,
            family=badge.family.value,
            label=badge.label,
            earned_message=badge.earned_message,
        )
        for badge in BADGES_BY_ID.values()
    ]


@router.get("/next", response_model=list[RecommendationOut], summary="What to do next")
async def what_next(
    principal: CurrentUser,
    session: Session,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> list[RecommendationOut]:
    """The next few things, each with a reason the learner can read."""
    now = datetime.now(timezone.utc)

    cards = {
        card.block_id: card
        for card in (
            await session.execute(select(CardRow).where(CardRow.user_id == principal.user_id))
        ).scalars()
    }

    profile = await ProfileRepository(session).current(principal.user_id) or {}
    goals = profile.get("goals") or {}

    candidates = []
    for block in load_blocks():
        card = cards.get(block["id"])
        phonemes = tuple((block.get("representations", {}).get("phonemes") or "").split())

        candidates.append(
            Candidate(
                block_id=block["id"],
                difficulty=block["difficulty"],
                phonemes=phonemes,
                scenario_tags=tuple(block.get("scenario_tags", [])),
                due_at=card.due_at if card else None,
                is_new=card is None,
                # A lapse recorded in the last day stands in for "this went
                # badly recently" until the speech pipeline supplies something
                # more precise (M7).
                last_failed_at=(
                    card.last_reviewed_at
                    if card and card.lapses > 0 and card.last_reviewed_at
                    and now - card.last_reviewed_at < timedelta(days=1)
                    else None
                ),
            )
        )

    context = LearnerContext(
        # Populated from the speech pipeline once GOP is live; empty is honest
        # rather than invented, and the recommender simply weights other signals.
        weak_phonemes=(),
        job_context=goals.get("job_context", ""),
        goal_tags=tuple(goals.get("target_scenarios", [])),
        now=now,
    )

    results = []
    for pick in recommend(candidates, context, limit=limit):
        block = get_block(pick.block_id)
        if block is None:  # pragma: no cover - build/serve mismatch
            continue
        results.append(
            RecommendationOut(
                block_id=pick.block_id,
                canonical_text=block["canonical_text"],
                explanation=pick.explanation,
                reason=pick.reason.value,
            )
        )

    return results

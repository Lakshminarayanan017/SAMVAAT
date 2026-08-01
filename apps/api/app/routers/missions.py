"""Missions (Blueprint Phase 2).

Turns a level into the missions a learner actually does, weighted by their
learning profile.

WHAT IS DELIBERATELY ABSENT
---------------------------
There is no `POST /missions/{id}/answer`. Answers already have a home:
`POST /practice/review`, which owns FSRS scheduling, XP and the grade derived
from observable behaviour. A second answer endpoint would mean two places
deciding what an attempt means, and they would disagree within a month.

So a mission is a *presentation* of a phrase the practice loop already knows how
to score. That is also what keeps the five §7.4 properties true without
re-proving them: XP still cannot see correctness, grading still cannot see
timing, and a scaffold still lowers the grade without touching XP — because none
of that moved.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.learning.curriculum import get_level
from app.learning.missions import MAX_MISSIONS, build_missions
from app.repositories.learners import ProfileRepository
from app.security.auth import CurrentUser

router = APIRouter(prefix="/missions", tags=["missions"])

Session = Annotated[AsyncSession, Depends(get_session)]


class MissionOut(BaseModel):
    id: str
    type: str
    block_id: str
    prompt: str
    #: Present only for choice missions, already shuffled.
    options: list[str] = []
    #: Always present. A mission with no way to ask for help is one a learner
    #: can get stuck in.
    scaffold: str
    #: Held back until the learner has answered, so it cannot be read off the
    #: wire before attempting. Not a security boundary — the phrase bank is
    #: public curriculum — but sending the answer alongside the question makes
    #: the mission pointless for anyone who opens dev tools, including the
    #: learner who then feels the practice was fake.
    coaching: str = ""


class MissionPlanOut(BaseModel):
    level_id: str
    title: str
    world_title: str
    sensitive: bool
    total: int
    missions: list[MissionOut]


@router.get(
    "/level/{level_id}",
    response_model=MissionPlanOut,
    summary="The missions for one level",
)
async def missions_for_level(
    level_id: str, principal: CurrentUser, session: Session
) -> MissionPlanOut:
    from app.learning.content import get_block
    from app.learning.curriculum import get_world

    level = get_level(level_id)
    if level is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"error": "unknown_level", "message": "We could not find that level."},
        )

    world = get_world(level.world_id)
    chapter = (
        next((c for c in world.chapters if c.id == level.chapter_id), None) if world else None
    )

    phrases = []
    for block_id in level.block_ids:
        block = get_block(block_id)
        if block is None:  # pragma: no cover - build/serve mismatch
            continue
        phrases.append({"block_id": block_id, "canonical_text": block["canonical_text"]})

    plan = build_missions(
        level_id=level.id,
        declared_types=list(level.missions),
        phrases=phrases,
        weights=await _weights_for(session, principal.user_id),
        # Stable per learner per level: reopening mid-session must not reshuffle
        # into different missions, and two learners should not get the same one.
        seed=f"{principal.user_id}:{level.id}",
    )

    return MissionPlanOut(
        level_id=plan.level_id,
        title=level.title,
        world_title=world.title if world else "",
        sensitive=chapter.sensitive if chapter else False,
        total=plan.total,
        missions=[
            MissionOut(
                id=mission.id,
                type=mission.type,
                block_id=mission.block_id,
                prompt=mission.prompt,
                options=list(mission.options),
                scaffold=mission.scaffold,
            )
            for mission in plan.missions[:MAX_MISSIONS]
        ],
    )


async def _weights_for(session: AsyncSession, user_id: str) -> dict[str, float] | None:
    """Mission weights from the learner's chosen preset, if they chose one.

    `None` when they did not, which the generator reads as an even mix. "I would
    rather not say" is a complete answer, and it must not produce a worse
    experience than naming a condition would (Blueprint §12.1).
    """
    from app.learning.curriculum import get_profile

    profile = await ProfileRepository(session).current(user_id)
    if not profile:
        return None

    preset_id = profile.get("learning_profile_id")
    if not preset_id:
        return None

    preset = get_profile(preset_id)
    if not preset:
        return None

    weights = preset.get("mission_weights")
    return dict(weights) if weights else None

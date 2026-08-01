"""The learning journey — worlds, levels, stars (the game layer).

    GET /journey            the whole map, for this learner
    GET /journey/level/{id} one level, with its phrases resolved
    GET /journey/profiles   the learning-profile presets

Everything here is one learner measured against themselves. There is no
argument, field or query by which another learner could enter — the same
constraint the progress router holds, for the same reason.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.learning.content import get_block
from app.learning.curriculum import get_level, load_profiles
from app.learning.fsrs import CardState
from app.learning.progression import Journey, build_journey
from app.models.tables import CardRow
from app.security.auth import CurrentUser

router = APIRouter(prefix="/journey", tags=["journey"])

Session = Annotated[AsyncSession, Depends(get_session)]


class LevelOut(BaseModel):
    level_id: str
    title: str
    missions: list[str]
    status: str
    stars: int
    #: 0-1. Phrases in this level the learner has met.
    coverage: float
    #: 0-1. Phrases that have stuck. Drives the third star.
    retention: float
    effort: int
    #: Shown under the tile. Written, not generated.
    caption: str


class ChapterOut(BaseModel):
    chapter_id: str
    title: str
    #: Disclosure content. The client shows an explicit exit and a route to a
    #: person on every screen of a sensitive chapter.
    sensitive: bool
    levels: list[LevelOut]
    stars: int
    max_stars: int


class WorldOut(BaseModel):
    world_id: str
    order: int
    title: str
    subtitle: str
    easy_read_title: str
    why: str
    colour: str
    icon: str
    flagship: bool
    is_current: bool
    caption: str
    chapters: list[ChapterOut]
    stars: int
    max_stars: int


class JourneyOut(BaseModel):
    worlds: list[WorldOut]
    total_stars: int
    max_stars: int
    #: Where the "continue" button goes. None only when everything is finished,
    #: which is a celebrated state rather than an empty one.
    next_level_id: str | None
    headline: str


class LevelPhrase(BaseModel):
    block_id: str
    canonical_text: str
    difficulty: int
    #: Whether the learner has met this one before. Drives "new" badging in the
    #: level intro, so nothing arrives unannounced.
    is_new: bool


class LevelDetailOut(BaseModel):
    level_id: str
    title: str
    world_id: str
    world_title: str
    chapter_id: str
    missions: list[str]
    effort: int
    sensitive: bool
    phrases: list[LevelPhrase]


class ProfileOut(BaseModel):
    id: str
    order: int
    label: str
    easy_read_label: str
    blurb: str
    #: What choosing this actually changes. Sent so the onboarding screen can
    #: show it before the learner commits — a preset that silently rewires the
    #: app is a preset nobody trusts.
    channels: dict
    presentation: dict = Field(default_factory=dict)
    interaction: dict = Field(default_factory=dict)
    session_minutes: int
    strategies: list[str] = Field(default_factory=list)


async def _cards(session: AsyncSession, user_id: str) -> dict[str, CardState]:
    rows = (
        await session.execute(select(CardRow).where(CardRow.user_id == user_id))
    ).scalars()

    return {
        row.block_id: CardState(
            stability=row.stability,
            difficulty=row.difficulty,
            due_at=row.due_at,
            reps=row.reps,
            lapses=row.lapses,
            last_reviewed_at=row.last_reviewed_at,
        )
        for row in rows
    }


def _to_out(journey: Journey) -> JourneyOut:
    return JourneyOut(
        worlds=[
            WorldOut(
                world_id=world.world_id,
                order=world.order,
                title=world.title,
                subtitle=world.subtitle,
                easy_read_title=world.easy_read_title,
                why=world.why,
                colour=world.colour,
                icon=world.icon,
                flagship=world.flagship,
                is_current=world.is_current,
                caption=world.caption,
                stars=world.stars,
                max_stars=world.max_stars,
                chapters=[
                    ChapterOut(
                        chapter_id=chapter.chapter_id,
                        title=chapter.title,
                        sensitive=chapter.sensitive,
                        stars=chapter.stars,
                        max_stars=chapter.max_stars,
                        levels=[
                            LevelOut(
                                level_id=level.level_id,
                                title=level.title,
                                missions=list(level.missions),
                                status=level.status.value,
                                stars=level.stars,
                                coverage=level.coverage,
                                retention=level.retention,
                                effort=level.effort,
                                caption=level.caption,
                            )
                            for level in chapter.levels
                        ],
                    )
                    for chapter in world.chapters
                ],
            )
            for world in journey.worlds
        ],
        total_stars=journey.total_stars,
        max_stars=journey.max_stars,
        next_level_id=journey.next_level_id,
        headline=journey.headline,
    )


@router.get("", response_model=JourneyOut, summary="The whole map")
async def my_journey(principal: CurrentUser, session: Session) -> JourneyOut:
    """Every world and level, with this learner's stars.

    Rebuilt from review history rather than stored as a progress record. A
    stored counter that disagrees with the history is a counter nobody can
    defend, and this one is shown to trainers.
    """
    return _to_out(build_journey(await _cards(session, principal.user_id)))


@router.get("/profiles", response_model=list[ProfileOut], summary="Learning presets")
async def profiles() -> list[ProfileOut]:
    """The presets offered during onboarding.

    NOT diagnoses, and never stored as one. A preset configures channels,
    mission mix, pacing and coaching strategies in one choice, and every setting
    it applies stays individually changeable afterwards.
    """
    return [
        ProfileOut(
            id=profile["id"],
            order=profile["order"],
            label=profile["label"],
            easy_read_label=profile["easy_read_label"],
            blurb=profile["blurb"],
            channels=profile["channels"],
            presentation=profile.get("presentation", {}),
            interaction=profile.get("interaction", {}),
            session_minutes=profile["session_minutes"],
            strategies=profile.get("strategies", []),
        )
        for profile in sorted(load_profiles()["profiles"], key=lambda p: p["order"])
    ]


@router.get("/level/{level_id}", response_model=LevelDetailOut, summary="One level")
async def level_detail(
    level_id: str, principal: CurrentUser, session: Session
) -> LevelDetailOut:
    from app.learning.curriculum import get_world

    level = get_level(level_id)

    if level is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"error": "unknown_level", "message": "We could not find that level."},
        )

    world = get_world(level.world_id)
    chapter = next(
        (c for c in world.chapters if c.id == level.chapter_id), None
    ) if world else None

    seen = set((await _cards(session, principal.user_id)).keys())

    phrases = []
    for block_id in level.block_ids:
        block = get_block(block_id)
        if block is None:  # pragma: no cover - build/serve mismatch
            continue
        phrases.append(
            LevelPhrase(
                block_id=block_id,
                canonical_text=block["canonical_text"],
                difficulty=block["difficulty"],
                is_new=block_id not in seen,
            )
        )

    return LevelDetailOut(
        level_id=level.id,
        title=level.title,
        world_id=level.world_id,
        world_title=world.title if world else "",
        chapter_id=level.chapter_id,
        missions=list(level.missions),
        effort=level.effort,
        sensitive=chapter.sensitive if chapter else False,
        phrases=phrases,
    )

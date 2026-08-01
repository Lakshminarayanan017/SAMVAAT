"""Progression — worlds, levels, stars and unlocking.

The game layer. What makes it a game rather than a course is that progress is
visible, granular and always moving; what makes it OUR game is what it refuses
to do.

THREE MECHANICS WE DO NOT BUILD, AND WHY
----------------------------------------
**No hearts, no energy, no lives.** Running out of attempts punishes an absence
of skill, and for our learners that absence is the disability. A learner with
dysarthria would exhaust a heart bar every session and be locked out of the
product for being disabled. Retries are unlimited, permanently.

**No leaderboard.** ADR-0003 applies to motivation as strictly as to scoring. A
learner who stammers placed beside one who does not will always be below them,
and the number will be both true and useless. The only rival is your own record.

**No hard locks.** A level ahead of you is `AVAILABLE_EARLY`, not `LOCKED` —
recommended order, never enforced order. Ethics E7 says a feature that fails a
persona is not shippable, and a gate that a learner cannot pass is a gate that
fails them permanently. Mastery is required for STARS, which are optional, not
for ACCESS, which is not.

STARS MEASURE RETENTION, NOT PERFORMANCE
----------------------------------------
    ★     you finished the level
    ★★    every phrase in it has been right at least once
    ★★★   every phrase has stuck — survived to a 21-day review interval

The third star cannot be earned in one sitting by anybody, however able. It is
earned by coming back, which is exactly the behaviour we want and the one thing
a fast talker has no advantage at.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.learning.curriculum import Level, World, load_curriculum
from app.learning.fsrs import CardState

#: Days of FSRS stability at which a phrase counts as having stuck. Matches the
#: `MASTERY_STABILITY_DAYS` the progress router already uses — one definition of
#: "reliable" across the product, or the dashboard and the star disagree.
RELIABLE_STABILITY_DAYS = 21.0

#: Proportion of a world's levels finished before the next world is RECOMMENDED.
#: Not required — nothing here is required — but it is what moves the "continue"
#: button on.
WORLD_ADVANCE_FRACTION = 0.6

MAX_STARS = 3


class LevelStatus(str, Enum):
    """Note what is missing: there is no LOCKED."""

    #: Finished at least once.
    COMPLETE = "complete"
    #: Started, not finished. Resumable exactly where it stopped.
    IN_PROGRESS = "in_progress"
    #: The next thing we suggest.
    RECOMMENDED = "recommended"
    #: Further ahead than we would suggest, and open anyway. The client says
    #: "this one is further on — you can still try it" rather than showing a
    #: padlock, because a padlock on a disability-adapted product reads as
    #: "not for you".
    AVAILABLE_EARLY = "available_early"


@dataclass(frozen=True)
class LevelProgress:
    level_id: str
    title: str
    missions: tuple[str, ...]
    status: LevelStatus
    stars: int
    #: 0.0-1.0. Phrases in this level the learner has met at all.
    coverage: float
    #: 0.0-1.0. Phrases that have stuck. Drives the third star.
    retention: float
    effort: int
    #: What the learner reads under the level. Written, not generated.
    caption: str


@dataclass(frozen=True)
class ChapterProgress:
    chapter_id: str
    title: str
    sensitive: bool
    levels: tuple[LevelProgress, ...]

    @property
    def stars(self) -> int:
        return sum(level.stars for level in self.levels)

    @property
    def max_stars(self) -> int:
        return len(self.levels) * MAX_STARS


@dataclass(frozen=True)
class WorldProgress:
    world_id: str
    order: int
    title: str
    subtitle: str
    easy_read_title: str
    why: str
    colour: str
    icon: str
    flagship: bool
    chapters: tuple[ChapterProgress, ...]
    #: True when this is where the "continue" button points.
    is_current: bool
    caption: str

    @property
    def levels(self) -> tuple[LevelProgress, ...]:
        return tuple(level for chapter in self.chapters for level in chapter.levels)

    @property
    def stars(self) -> int:
        return sum(chapter.stars for chapter in self.chapters)

    @property
    def max_stars(self) -> int:
        return sum(chapter.max_stars for chapter in self.chapters)

    @property
    def complete_levels(self) -> int:
        return sum(1 for level in self.levels if level.status is LevelStatus.COMPLETE)


@dataclass(frozen=True)
class Journey:
    """The whole map."""

    worlds: tuple[WorldProgress, ...]
    total_stars: int
    max_stars: int
    #: The single level the "continue" button opens. None only when every level
    #: in the product is complete, which is a real and celebrated state.
    next_level_id: str | None
    headline: str


def stars_for(level: Level, cards: dict[str, CardState]) -> tuple[int, float, float]:
    """Stars, coverage and retention for one level.

    Returns `(stars, coverage, retention)`.

    A level with no phrases — a pure interview level, say — is scored on whether
    it was attempted at all, since there is nothing to retain.
    """
    if not level.block_ids:
        return 0, 0.0, 0.0

    met = [cards[block_id] for block_id in level.block_ids if block_id in cards]
    total = len(level.block_ids)

    coverage = len(met) / total

    # "Right at least once" is reps beyond the lapses: a card reviewed three
    # times with three lapses has never actually been right.
    correct_once = sum(1 for card in met if card.reps > card.lapses)
    reliable = sum(1 for card in met if card.stability >= RELIABLE_STABILITY_DAYS)

    retention = reliable / total

    # The first star needs FULL coverage, not any coverage. Levels overlap by
    # design — a chapter's closing level draws on everything before it — so
    # "met one phrase" would mark the closing level finished the moment the
    # first level was, and hand the learner a completion they did not earn.
    stars = 0
    if len(met) == total:
        stars = 1
    if correct_once == total:
        stars = 2
    if reliable == total:
        stars = 3

    return stars, coverage, retention


def _level_caption(status: LevelStatus, stars: int) -> str:
    """The line under a level tile.

    Warm, specific, and never scolding. `AVAILABLE_EARLY` in particular has to
    read as an open door rather than a warning.
    """
    if stars == MAX_STARS:
        return "You know these. All three stars."
    if status is LevelStatus.COMPLETE:
        return "Finished. Come back to make it stick."
    if status is LevelStatus.IN_PROGRESS:
        return "Picks up where you left off."
    if status is LevelStatus.AVAILABLE_EARLY:
        return "Further on — you can still try it."
    return "Start here."


def _world_caption(world: World, complete: int, is_current: bool) -> str:
    total = len(world.levels)

    if complete == 0:
        return world.why
    if complete >= total:
        return "Every level finished. Come back for the stars."
    if is_current:
        return f"{complete} of {total} levels finished. Keep going."
    return f"{complete} of {total} levels finished."


def build_journey(
    cards: dict[str, CardState],
    started_level_ids: set[str] | None = None,
) -> Journey:
    """The whole map, for one learner.

    Args:
        cards: FSRS state per block id. The single source of what the learner
            has actually done — rebuilt from review history rather than stored
            as a separate progress counter, because a counter that disagrees
            with the history is a counter nobody can defend.
        started_level_ids: levels opened but not finished.
    """
    started = started_level_ids or set()
    worlds: list[WorldProgress] = []

    # The first world that is not yet advanced-past is where "continue" points.
    current_world_id: str | None = None
    next_level_id: str | None = None

    for world in load_curriculum():
        complete_count = 0
        chapters: list[ChapterProgress] = []

        for chapter in world.chapters:
            levels: list[LevelProgress] = []

            for level in chapter.levels:
                stars, coverage, retention = stars_for(level, cards)

                if stars >= 1:
                    status = LevelStatus.COMPLETE
                    complete_count += 1
                elif level.id in started:
                    # Only a level the learner actually OPENED is in progress.
                    # Coverage cannot stand in for that: levels overlap by
                    # design, so a chapter's closing level always shows partial
                    # coverage the moment any earlier level is done, and reading
                    # that as "you started this" would show half the map as
                    # half-finished work nobody began.
                    status = LevelStatus.IN_PROGRESS
                else:
                    # Resolved below once we know where the learner is up to.
                    status = LevelStatus.AVAILABLE_EARLY

                levels.append(
                    LevelProgress(
                        level_id=level.id,
                        title=level.title,
                        missions=level.missions,
                        status=status,
                        stars=stars,
                        coverage=round(coverage, 3),
                        retention=round(retention, 3),
                        effort=level.effort,
                        caption=_level_caption(status, stars),
                    )
                )

            chapters.append(
                ChapterProgress(
                    chapter_id=chapter.id,
                    title=chapter.title,
                    sensitive=chapter.sensitive,
                    levels=tuple(levels),
                )
            )

        advanced = complete_count >= max(1, round(len(world.levels) * WORLD_ADVANCE_FRACTION))
        is_current = current_world_id is None and not advanced

        if is_current:
            current_world_id = world.id

        worlds.append(
            WorldProgress(
                world_id=world.id,
                order=world.order,
                title=world.title,
                subtitle=world.subtitle,
                easy_read_title=world.easy_read_title,
                why=world.why,
                colour=world.colour,
                icon=world.icon,
                flagship=world.flagship,
                chapters=tuple(chapters),
                is_current=is_current,
                caption=_world_caption(world, complete_count, is_current),
            )
        )

    worlds = _mark_recommended(worlds, current_world_id)

    for world in worlds:
        for level in world.levels:
            if level.status in (LevelStatus.RECOMMENDED, LevelStatus.IN_PROGRESS):
                next_level_id = level.level_id
                break
        if next_level_id:
            break

    total_stars = sum(world.stars for world in worlds)
    max_stars = sum(world.max_stars for world in worlds)

    return Journey(
        worlds=tuple(worlds),
        total_stars=total_stars,
        max_stars=max_stars,
        next_level_id=next_level_id,
        headline=_headline(total_stars, max_stars, next_level_id),
    )


def _mark_recommended(
    worlds: list[WorldProgress], current_world_id: str | None
) -> list[WorldProgress]:
    """Promote exactly one level to RECOMMENDED.

    The first unstarted level in the current world. Everything else that is not
    complete or in progress stays AVAILABLE_EARLY — open, just not suggested.
    """
    from dataclasses import replace

    promoted = False
    updated: list[WorldProgress] = []

    for world in worlds:
        # An unfinished level the learner already opened IS the recommendation.
        # Promoting a second one beside it offers two "next" things, and the
        # learner has to decide which of our suggestions to trust.
        already_underway = any(
            level.status is LevelStatus.IN_PROGRESS for level in world.levels
        )

        if promoted or already_underway or world.world_id != current_world_id:
            updated.append(world)
            continue

        chapters: list[ChapterProgress] = []

        for chapter in world.chapters:
            levels: list[LevelProgress] = []

            for level in chapter.levels:
                if not promoted and level.status is LevelStatus.AVAILABLE_EARLY:
                    promoted = True
                    levels.append(
                        replace(
                            level,
                            status=LevelStatus.RECOMMENDED,
                            caption=_level_caption(LevelStatus.RECOMMENDED, level.stars),
                        )
                    )
                else:
                    levels.append(level)

            chapters.append(replace(chapter, levels=tuple(levels)))

        updated.append(replace(world, chapters=tuple(chapters)))

    return updated


def _headline(total_stars: int, max_stars: int, next_level_id: str | None) -> str:
    """The line at the top of the map.

    Never a percentage of the whole product. "3% complete" on day one is
    accurate and demoralising; "two stars so far" is accurate and additive.
    """
    if next_level_id is None:
        return "You have finished every level. That is the whole journey."
    if total_stars == 0:
        return "Ten worlds ahead of you. Start wherever you like."
    if total_stars == 1:
        return "One star so far."
    return f"{total_stars} stars so far."


def levels_for_world(world_id: str) -> tuple[Level, ...]:
    from app.learning.curriculum import get_world

    world = get_world(world_id)
    return world.levels if world else ()


def world_of(level_id: str) -> World | None:
    from app.learning.curriculum import get_level, get_world

    level = get_level(level_id)
    return get_world(level.world_id) if level else None

"""Access to the built learning journey.

Reads `packages/content/dist/curriculum.json`, the artefact the content build
resolved against the real phrase bank. The API serves the same journey the
client renders, so the two can never disagree about what a level contains.

Loaded once and cached. Fifty levels is small, and re-reading per request would
be pointless I/O on a host we are trying to keep inside a free tier.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _repository_root() -> Path:
    for directory in Path(__file__).resolve().parents:
        if (directory / "package.json").exists() and (directory / "packages").is_dir():
            return directory
    raise RuntimeError("Could not locate the repository root from app/learning/curriculum.py")


_DIST = _repository_root() / "packages" / "content" / "dist"


@dataclass(frozen=True)
class Level:
    id: str
    title: str
    missions: tuple[str, ...]
    block_ids: tuple[str, ...]
    #: Sum of the mission efforts. XP is paid on this, never on score.
    effort: int
    chapter_id: str
    world_id: str


@dataclass(frozen=True)
class Chapter:
    id: str
    title: str
    #: Disclosure and self-advocacy content. The client shows an explicit exit
    #: and a route to a human on every screen of a sensitive chapter.
    sensitive: bool
    levels: tuple[Level, ...]
    world_id: str


@dataclass(frozen=True)
class World:
    id: str
    order: int
    title: str
    subtitle: str
    easy_read_title: str
    why: str
    colour: str
    icon: str
    flagship: bool
    chapters: tuple[Chapter, ...]
    block_ids: tuple[str, ...]

    @property
    def levels(self) -> tuple[Level, ...]:
        return tuple(level for chapter in self.chapters for level in chapter.levels)


@lru_cache(maxsize=1)
def load_curriculum() -> tuple[World, ...]:
    """Every world, in order.

    Raises with an actionable message rather than returning empty. A silently
    empty curriculum surfaces as "there is nothing to learn", which is a
    confusing way to discover you skipped a build step.
    """
    path = _DIST / "curriculum.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Curriculum not found at {path}.\n"
            "Run `npm run content:build` from the repository root."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))

    return tuple(
        World(
            id=world["id"],
            order=world["order"],
            title=world["title"],
            subtitle=world["subtitle"],
            easy_read_title=world["easy_read_title"],
            why=world["why"],
            colour=world["colour"],
            icon=world["icon"],
            flagship=world["flagship"],
            block_ids=tuple(world["block_ids"]),
            chapters=tuple(
                Chapter(
                    id=chapter["id"],
                    title=chapter["title"],
                    sensitive=chapter["sensitive"],
                    world_id=world["id"],
                    levels=tuple(
                        Level(
                            id=level["id"],
                            title=level["title"],
                            missions=tuple(level["missions"]),
                            block_ids=tuple(level["block_ids"]),
                            effort=level["effort"],
                            chapter_id=chapter["id"],
                            world_id=world["id"],
                        )
                        for level in chapter["levels"]
                    ),
                )
                for chapter in world["chapters"]
            ),
        )
        for world in sorted(payload["worlds"], key=lambda world: world["order"])
    )


@lru_cache(maxsize=1)
def levels_by_id() -> dict[str, Level]:
    return {
        level.id: level
        for world in load_curriculum()
        for chapter in world.chapters
        for level in chapter.levels
    }


@lru_cache(maxsize=1)
def worlds_by_id() -> dict[str, World]:
    return {world.id: world for world in load_curriculum()}


def get_level(level_id: str) -> Level | None:
    return levels_by_id().get(level_id)


def get_world(world_id: str) -> World | None:
    return worlds_by_id().get(world_id)


@lru_cache(maxsize=1)
def load_profiles() -> dict:
    """The learning-profile presets.

    Returns an empty structure rather than raising when the file is absent: a
    missing profile catalogue costs personalisation, which degrades the product,
    while a missing curriculum costs the product entirely. Different failures
    deserve different severity.
    """
    path = _DIST / "profiles.json"

    if not path.exists():
        return {"profiles": [], "strategies": {}}

    return json.loads(path.read_text(encoding="utf-8"))


def get_profile(profile_id: str) -> dict | None:
    return next(
        (p for p in load_profiles().get("profiles", []) if p["id"] == profile_id), None
    )

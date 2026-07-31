"""Access to the built Workplace Language Bank.

Reads `packages/content/dist/blocks.json`, the artefact the content validator
checked. Loaded once and cached — 226 blocks is small, and re-reading per
request would be pointless I/O.

The API serves content from the same build the client renders, so the two can
never disagree about what a phrase is.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _repository_root() -> Path:
    """Walk up to the monorepo root.

    Counting `parents[n]` breaks the moment a module moves to a different depth,
    and does so with a confusing "file not found" rather than an obvious error.
    Searching for the workspace marker is stable under refactoring.
    """
    for directory in Path(__file__).resolve().parents:
        if (directory / "package.json").exists() and (directory / "packages").is_dir():
            return directory
    raise RuntimeError("Could not locate the repository root from app/learning/content.py")


_BLOCKS_PATH = _repository_root() / "packages" / "content" / "dist" / "blocks.json"


@lru_cache(maxsize=1)
def load_blocks() -> list[dict]:
    """All ContentBlocks in the bank.

    Raises with an actionable message rather than an empty list — a silently
    empty phrase bank would surface as "there is nothing to practise", which is
    a confusing way to learn you forgot a build step.
    """
    if not _BLOCKS_PATH.exists():
        raise FileNotFoundError(
            f"Workplace Language Bank not found at {_BLOCKS_PATH}.\n"
            "Run `npm run content:build` from the repository root."
        )
    return json.loads(_BLOCKS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def blocks_by_id() -> dict[str, dict]:
    return {block["id"]: block for block in load_blocks()}


def get_block(block_id: str) -> dict | None:
    return blocks_by_id().get(block_id)

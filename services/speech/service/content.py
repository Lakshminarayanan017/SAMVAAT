"""Read access to the built Workplace Language Bank.

The speech service needs the corpus for exactly one thing: choosing enrolment
phrases with good phonetic coverage. It reads the same built artefact the API
serves and the client renders, so all three can never disagree about what a
phrase is.

Read-only and cached. The speech service never writes content.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("samvaad.speech.content")


def _repository_root() -> Path:
    """Walk up to the monorepo root.

    Searching for the workspace marker rather than counting `parents[n]`: the
    count breaks the moment a module moves depth, and it breaks with a
    confusing "file not found" rather than an obvious error.
    """
    for directory in Path(__file__).resolve().parents:
        if (directory / "package.json").exists() and (directory / "packages").is_dir():
            return directory
    raise RuntimeError("Could not locate the repository root from service/content.py")


@lru_cache(maxsize=1)
def load_blocks() -> list[dict]:
    """All ContentBlocks, or an empty list if the bank has not been built.

    Empty rather than raising, unlike the API's equivalent. The API cannot serve
    a practice session without content and should fail loudly; the speech
    service only needs content for enrolment phrase selection, and refusing to
    start the whole ASR pipeline because a Node build step was skipped would
    take down speech analysis for a reason that has nothing to do with it.
    """
    path = _repository_root() / "packages" / "content" / "dist" / "blocks.json"

    if not path.exists():
        log.warning(
            "Workplace Language Bank not found at %s; enrolment phrase selection is "
            "unavailable. Run `npm run content:build` from the repository root.",
            path,
        )
        return []

    return json.loads(path.read_text(encoding="utf-8"))

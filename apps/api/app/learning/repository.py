"""Card storage.

An in-memory implementation behind a Protocol, because the database lands in M1
and the practice loop should not wait for it. When the Postgres implementation
arrives it satisfies the same Protocol and `build_session` never changes.

THIS IS TEMPORARY AND NOT PERSISTENT. State is lost on restart. It is here so
the loop is demonstrable end to end, not because in-memory storage is adequate.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from app.learning.fsrs import CardState


class CardRepository(Protocol):
    """The seam the Postgres implementation will fill in M1."""

    def get(self, user_id: str, block_id: str) -> CardState | None: ...

    def all_for_user(self, user_id: str) -> dict[str, CardState]: ...

    def save(self, user_id: str, block_id: str, card: CardState) -> None: ...


class InMemoryCardRepository:
    """Development-only card store."""

    def __init__(self) -> None:
        self._cards: dict[str, dict[str, CardState]] = defaultdict(dict)

    def get(self, user_id: str, block_id: str) -> CardState | None:
        return self._cards[user_id].get(block_id)

    def all_for_user(self, user_id: str) -> dict[str, CardState]:
        return dict(self._cards[user_id])

    def save(self, user_id: str, block_id: str, card: CardState) -> None:
        self._cards[user_id][block_id] = card

    def clear(self) -> None:
        self._cards.clear()

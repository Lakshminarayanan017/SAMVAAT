"""Conversation state for role-play and mock interviews.

The GenAI service is stateless — state travels with each request — so the
gateway is what remembers a conversation between turns. That is the right split:
the gateway is already the only thing that talks to the database (ADR-0004), and
it means the GenAI service can be restarted or scaled to zero mid-interview
without anyone losing their place.

WHY THIS EXISTS RATHER THAN A DICT IN THE ROUTER
------------------------------------------------
Ethics E6 says an interview must be pausable and resumable. A learner with
fatigue, anxiety or a fluctuating condition needs to be able to stop at question
four and come back tomorrow — and a conversation stored in a request handler
cannot survive that.

In-memory behind a Protocol until the database lands in M1, same as the card
repository.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

Kind = Literal["roleplay", "interview"]


@dataclass
class Conversation:
    """One role-play or interview, and everything needed to resume it."""

    id: str
    user_id: str
    kind: Kind
    #: The opaque state blob the GenAI service round-trips. The gateway stores
    #: it and never interprets it — the shape belongs to the GenAI service, and
    #: parsing it here would couple the two services together needlessly.
    state: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    #: Question/answer pairs, kept so a score can be requested later and so a
    #: learner can replay their own answers.
    exchanges: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


class ConversationStore(Protocol):
    """The seam the Postgres implementation fills in M1."""

    def get(self, conversation_id: str) -> Conversation | None: ...

    def save(self, conversation: Conversation) -> None: ...

    def list_for_user(self, user_id: str, kind: Kind | None = None) -> list[Conversation]: ...

    def delete_for_user(self, user_id: str) -> int: ...


class InMemoryConversationStore:
    """Development-only. Not persistent, and marked as such."""

    def __init__(self) -> None:
        self._by_id: dict[str, Conversation] = {}
        self._by_user: dict[str, list[str]] = defaultdict(list)

    def get(self, conversation_id: str) -> Conversation | None:
        return self._by_id.get(conversation_id)

    def save(self, conversation: Conversation) -> None:
        if conversation.id not in self._by_id:
            self._by_user[conversation.user_id].append(conversation.id)
        conversation.touch()
        self._by_id[conversation.id] = conversation

    def list_for_user(self, user_id: str, kind: Kind | None = None) -> list[Conversation]:
        found = [self._by_id[i] for i in self._by_user.get(user_id, []) if i in self._by_id]
        if kind:
            found = [c for c in found if c.kind == kind]
        return sorted(found, key=lambda c: c.updated_at, reverse=True)

    def delete_for_user(self, user_id: str) -> int:
        """Part of the erasure path. A learner's rehearsed interview answers are
        as personal as anything else they give us."""
        ids = self._by_user.pop(user_id, [])
        for conversation_id in ids:
            self._by_id.pop(conversation_id, None)
        return len(ids)

    def clear(self) -> None:
        self._by_id.clear()
        self._by_user.clear()

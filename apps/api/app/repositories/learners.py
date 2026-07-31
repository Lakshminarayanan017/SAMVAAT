"""Persistence for learners, profiles, consent and conversations.

These fill the Protocols the in-memory stores were standing in for. The
`build_session`, `Fsrs` and router code above them does not change — which was
the point of putting a seam there in the first place.

Every method takes `user_id` and scopes on it. Not because a caller might forget
to filter, but because there is then no query in the codebase that *can* return
another learner's row. Defence at the query layer, not at the handler.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.learning.conversations import Conversation, Kind
from app.learning.fsrs import CardState
from app.models.tables import (
    AudioObjectRow,
    CapRow,
    CardRow,
    ConsentRow,
    ConversationRow,
    RubricAuditRow,
    User,
)
from app.security.consent import PURPOSES
from app.security.retention import AudioObject, RetentionReason


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: str, *, is_guest: bool = True, email: str | None = None
    ) -> User:
        user = User(id=user_id, is_guest=is_guest, email=email)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def touch(self, user_id: str) -> None:
        user = await self.get(user_id)
        if user:
            user.last_seen_at = utcnow()

    async def upgrade_guest(self, user_id: str, email: str) -> User | None:
        """Turn a guest into an account, in place.

        In place, not by creating a new user and copying: a learner who
        practised as a guest for a week and then signed up must keep every card,
        every conversation and every consent. Losing them would punish exactly
        the caution we wanted to allow.
        """
        user = await self.get(user_id)
        if user is None:
            return None
        user.email = email
        user.is_guest = False
        return user

    async def delete(self, user_id: str) -> None:
        """Erasure. Cascades to profiles; the other tables are cleared by their
        own repositories so each one can be tested in isolation."""
        await self.session.execute(delete(User).where(User.id == user_id))


class ProfileRepository:
    """Communication Ability Profiles. Versioned, never updated in place."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def current(self, user_id: str) -> dict | None:
        result = await self.session.execute(
            select(CapRow)
            .where(CapRow.user_id == user_id)
            .order_by(CapRow.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row.profile if row else None

    async def save(self, user_id: str, profile: dict) -> dict:
        """Write the next version. The previous one stays readable, which is
        what lets a trainer see that scores changed because the profile
        changed, not because the learner got worse."""
        result = await self.session.execute(
            select(CapRow.version)
            .where(CapRow.user_id == user_id)
            .order_by(CapRow.version.desc())
            .limit(1)
        )
        version = (result.scalar_one_or_none() or 0) + 1

        stored = {**profile, "user_id": user_id, "version": version}
        self.session.add(CapRow(user_id=user_id, version=version, profile=stored))
        await self.session.flush()
        return stored

    async def history(self, user_id: str) -> list[dict]:
        result = await self.session.execute(
            select(CapRow).where(CapRow.user_id == user_id).order_by(CapRow.version)
        )
        return [row.profile for row in result.scalars()]


class ConsentRepository:
    """Append-only ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_consent(self, user_id: str, purpose: str) -> bool:
        if purpose not in PURPOSES:
            raise ValueError(f"Unknown consent purpose '{purpose}'")

        result = await self.session.execute(
            select(ConsentRow.granted)
            .where(ConsentRow.user_id == user_id, ConsentRow.purpose == purpose)
            .order_by(ConsentRow.id.desc())
            .limit(1)
        )
        # Absence of a record is absence of consent.
        return bool(result.scalar_one_or_none())

    async def record(
        self, user_id: str, purpose: str, granted: bool, guardian_user_id: str | None = None
    ) -> None:
        if purpose not in PURPOSES:
            raise ValueError(f"Unknown consent purpose '{purpose}'")
        self.session.add(
            ConsentRow(
                user_id=user_id,
                purpose=purpose,
                granted=granted,
                guardian_user_id=guardian_user_id,
            )
        )
        await self.session.flush()

    async def granted(self, user_id: str) -> set[str]:
        return {p for p in PURPOSES if await self.has_consent(user_id, p)}

    async def history(self, user_id: str) -> list[ConsentRow]:
        result = await self.session.execute(
            select(ConsentRow).where(ConsentRow.user_id == user_id).order_by(ConsentRow.id)
        )
        return list(result.scalars())


class CardRepository:
    """FSRS card state. Fills the Protocol the in-memory store stood in for."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_state(row: CardRow) -> CardState:
        return CardState(
            stability=row.stability,
            difficulty=row.difficulty,
            due_at=row.due_at,
            reps=row.reps,
            lapses=row.lapses,
            last_reviewed_at=row.last_reviewed_at,
        )

    async def get(self, user_id: str, block_id: str) -> CardState | None:
        result = await self.session.execute(
            select(CardRow).where(CardRow.user_id == user_id, CardRow.block_id == block_id)
        )
        row = result.scalar_one_or_none()
        return self._to_state(row) if row else None

    async def all_for_user(self, user_id: str) -> dict[str, CardState]:
        result = await self.session.execute(select(CardRow).where(CardRow.user_id == user_id))
        return {row.block_id: self._to_state(row) for row in result.scalars()}

    async def save(self, user_id: str, block_id: str, card: CardState) -> None:
        result = await self.session.execute(
            select(CardRow).where(CardRow.user_id == user_id, CardRow.block_id == block_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            row = CardRow(user_id=user_id, block_id=block_id)
            self.session.add(row)

        row.stability = card.stability
        row.difficulty = card.difficulty
        row.due_at = card.due_at
        row.reps = card.reps
        row.lapses = card.lapses
        row.last_reviewed_at = card.last_reviewed_at
        await self.session.flush()

    async def delete_for_user(self, user_id: str) -> None:
        await self.session.execute(delete(CardRow).where(CardRow.user_id == user_id))


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(row: ConversationRow) -> Conversation:
        return Conversation(
            id=row.id,
            user_id=row.user_id,
            kind=row.kind,  # type: ignore[arg-type]
            state=row.state or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
            exchanges=list(row.exchanges or []),
            finished=row.finished,
        )

    async def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        """Scoped on user_id, so there is no query here that CAN return someone
        else's conversation."""
        result = await self.session.execute(
            select(ConversationRow).where(
                ConversationRow.id == conversation_id, ConversationRow.user_id == user_id
            )
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def save(self, conversation: Conversation) -> None:
        row = await self.session.get(ConversationRow, conversation.id)

        if row is None:
            row = ConversationRow(
                id=conversation.id, user_id=conversation.user_id, kind=conversation.kind
            )
            self.session.add(row)

        row.state = conversation.state
        # Reassigned rather than mutated: SQLAlchemy does not track in-place
        # changes to a JSON column, so appending to the list would be lost.
        row.exchanges = list(conversation.exchanges)
        row.finished = conversation.finished
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def list_for_user(self, user_id: str, kind: Kind | None = None) -> list[Conversation]:
        query = select(ConversationRow).where(ConversationRow.user_id == user_id)
        if kind:
            query = query.where(ConversationRow.kind == kind)

        result = await self.session.execute(query.order_by(ConversationRow.updated_at.desc()))
        return [self._to_domain(row) for row in result.scalars()]

    async def delete_for_user(self, user_id: str) -> int:
        result = await self.session.execute(
            delete(ConversationRow).where(ConversationRow.user_id == user_id)
        )
        return result.rowcount or 0


class AudioRepository:
    """Audio objects and their TTLs (Ethics E3)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_domain(row: AudioObjectRow) -> AudioObject:
        return AudioObject(
            key=row.key,
            user_id=row.user_id,
            reason=RetentionReason(row.reason),
            created_at=row.created_at,
            expires_at=row.expires_at,
        )

    async def put(self, obj: AudioObject) -> None:
        self.session.add(
            AudioObjectRow(
                key=obj.key,
                user_id=obj.user_id,
                reason=obj.reason.value,
                created_at=obj.created_at,
                expires_at=obj.expires_at,
            )
        )
        await self.session.flush()

    async def purge_expired(self, now: datetime | None = None) -> list[str]:
        now = now or datetime.now(timezone.utc)
        result = await self.session.execute(
            select(AudioObjectRow.key).where(
                AudioObjectRow.expires_at.is_not(None), AudioObjectRow.expires_at <= now
            )
        )
        keys = list(result.scalars())
        if keys:
            await self.session.execute(
                delete(AudioObjectRow).where(AudioObjectRow.key.in_(keys))
            )
        return keys

    async def purge_for_user(
        self, user_id: str, reason: RetentionReason | None = None
    ) -> list[str]:
        query = select(AudioObjectRow.key).where(AudioObjectRow.user_id == user_id)
        if reason:
            query = query.where(AudioObjectRow.reason == reason.value)

        keys = list((await self.session.execute(query)).scalars())
        if keys:
            await self.session.execute(delete(AudioObjectRow).where(AudioObjectRow.key.in_(keys)))
        return keys

    async def list_for_user(self, user_id: str) -> list[AudioObject]:
        result = await self.session.execute(
            select(AudioObjectRow).where(AudioObjectRow.user_id == user_id)
        )
        return [self._to_domain(row) for row in result.scalars()]


class AuditRepository:
    """Rubric audit records. Written once, never updated (Ethics E2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self, audit_id: str, user_id: str, audit: dict, conversation_id: str | None
    ) -> None:
        self.session.add(
            RubricAuditRow(
                id=audit_id,
                user_id=user_id,
                conversation_id=conversation_id,
                rubric_version=audit.get("rubric_version", ""),
                scored_dimensions=audit.get("scored_dimensions", []),
                excluded_dimensions=audit.get("excluded_dimensions", []),
                prompt_hash=audit.get("prompt_hash", ""),
                model_id=audit.get("model_id", ""),
                evidence=audit.get("evidence", {}),
            )
        )
        await self.session.flush()

    async def get(self, audit_id: str, user_id: str) -> RubricAuditRow | None:
        result = await self.session.execute(
            select(RubricAuditRow).where(
                RubricAuditRow.id == audit_id, RubricAuditRow.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def delete_for_user(self, user_id: str) -> None:
        await self.session.execute(delete(RubricAuditRow).where(RubricAuditRow.user_id == user_id))

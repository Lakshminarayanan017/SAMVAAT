"""The database schema.

Shapes follow docs/EXECUTION_PLAN.md §8. Three choices are worth stating,
because each encodes a rule from the Ethics Charter rather than a preference:

* **CAP rows are versioned, never updated.** Progress data records the version
  it was collected under, so a learner who switches from speech to symbols does
  not have their earlier scores silently reinterpreted.

* **Consent is an append-only ledger.** "When did this learner consent, and to
  what" must be answerable months later. An overwriting store cannot answer it.

* **Audio carries its expiry as a column.** Retention is a value the purge job
  enforces, not a promise in a policy document (Ethics E3).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UtcDateTime, utcnow


class User(Base):
    """A learner, trainer or institution admin.

    GUESTS ARE REAL USERS. Someone should be able to practise saying "good
    morning" without handing over an email address first — for a disabled
    learner deciding whether to trust us, that is not a small thing. A guest row
    is upgraded in place when they choose to sign up, so nothing is lost.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), default="learner")
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True)
    guardian_user_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.id"))
    institution_id: Mapped[str | None] = mapped_column(String(64), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="en-IN")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    profiles: Mapped[list[CapRow]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class CapRow(Base):
    """One version of a Communication Ability Profile.

    Never updated in place. `updateProfile` writes a new row with version+1, and
    the previous version stays readable — which is what lets a trainer see that
    a learner's scores changed because their profile changed, not because they
    got worse.
    """

    __tablename__ = "communication_ability_profiles"
    __table_args__ = (Index("ix_cap_user_version", "user_id", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    #: The whole CAP, validated against the JSON Schema before it is written.
    #: Stored as a document because the router reads it whole and never queries
    #: inside it — normalising would buy nothing and cost a join per render.
    profile: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="profiles")


class ConsentRow(Base):
    """Append-only consent ledger. One row per grant or revocation."""

    __tablename__ = "consents"
    __table_args__ = (Index("ix_consent_user_purpose", "user_id", "purpose"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    purpose: Mapped[str] = mapped_column(String(64))
    granted: Mapped[bool] = mapped_column(Boolean)
    guardian_user_id: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class CardRow(Base):
    """FSRS scheduling state for one phrase, for one learner."""

    __tablename__ = "practice_cards"
    __table_args__ = (Index("ix_card_user_due", "user_id", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    block_id: Mapped[str] = mapped_column(String(128))
    stability: Mapped[float] = mapped_column(Float)
    difficulty: Mapped[float] = mapped_column(Float)
    due_at: Mapped[datetime] = mapped_column(UtcDateTime)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class ConversationRow(Base):
    """A role-play or mock interview, and everything needed to resume it."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversation_user_kind", "user_id", "kind"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    #: Opaque to us. The shape belongs to the GenAI service, and parsing it here
    #: would couple two services that are deliberately independent.
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    exchanges: Mapped[list] = mapped_column(JSON, default=list)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)


class AudioObjectRow(Base):
    """A stored recording and the terms it is stored under (Ethics E3)."""

    __tablename__ = "audio_objects"
    __table_args__ = (Index("ix_audio_expiry", "expires_at"),)

    key: Mapped[str] = mapped_column(String(256), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    #: NULL means "kept while consent stands" — the research corpus case.
    #: Revoking that consent deletes the row, so NULL never means "forever".
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class RubricAuditRow(Base):
    """Layer four of the E2 enforcement.

    The GenAI service proves the rubric was blind to speech traits; this row is
    what makes it provable two years later, to someone who was not in the room.
    Never updated, never deleted by anything except a learner's erasure request.
    """

    __tablename__ = "rubric_audit"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    rubric_version: Mapped[str] = mapped_column(String(32))
    scored_dimensions: Mapped[list] = mapped_column(JSON, default=list)
    excluded_dimensions: Mapped[list] = mapped_column(JSON, default=list)
    prompt_hash: Mapped[str] = mapped_column(String(128), default="")
    model_id: Mapped[str] = mapped_column(String(128), default="")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    #: Set when a trainer overrides the AI (Ethics E5). Null until M14.
    trainer_override: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)

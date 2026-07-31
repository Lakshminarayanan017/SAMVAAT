"""Consent, enforced at the query layer.

The rule that makes this work: **consent is checked where data is accessed, not
where the UI decides what to show.** A UI-level check is one forgotten
conditional away from a leak, and the leak is silent. A ledger consulted by the
code that actually touches the data cannot be bypassed by forgetting.

Purposes are separate and independently revocable, because they are genuinely
different decisions. A learner may be happy for a trainer to hear a recording
and entirely unwilling for it to enter a research corpus, and collapsing those
into one "I agree" is not consent in any meaningful sense.

The full ledger with guardian flows and an audit trail lands in M17. This is the
enforcement seam, present from the moment the first byte of audio can be stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


class ConsentError(PermissionError):
    """Raised when an operation is attempted without the consent it requires."""

    def __init__(self, user_id: str, purpose: str) -> None:
        self.user_id = user_id
        self.purpose = purpose
        super().__init__(f"User '{user_id}' has not granted consent for '{purpose}'")


#: Every purpose the system recognises. Adding one is a deliberate act, so a new
#: feature cannot quietly widen what an existing consent covers.
PURPOSES = frozenset(
    {
        "basic_use",
        "speech_processing",
        "store_audio_for_review",
        "research_corpus",
        "trainer_visibility",
        "institution_analytics",
        "camera_on_device",
    }
)


@dataclass(frozen=True)
class ConsentRecord:
    user_id: str
    purpose: str
    granted: bool
    at: datetime
    #: Set when a guardian gave consent on the learner's behalf.
    guardian_user_id: str | None = None


class ConsentLedger(Protocol):
    def has_consent(self, user_id: str, purpose: str) -> bool: ...

    def record(self, record: ConsentRecord) -> None: ...

    def history(self, user_id: str) -> list[ConsentRecord]: ...


class InMemoryConsentLedger:
    """Development-only ledger. Append-only, like the real one will be.

    Append-only matters: "when did this learner consent, and to what" must be
    answerable months later, and an overwriting store cannot answer it.
    """

    def __init__(self) -> None:
        self._records: list[ConsentRecord] = []

    def has_consent(self, user_id: str, purpose: str) -> bool:
        if purpose not in PURPOSES:
            raise ValueError(f"Unknown consent purpose '{purpose}'")

        # Latest record wins; absence of a record is absence of consent.
        for record in reversed(self._records):
            if record.user_id == user_id and record.purpose == purpose:
                return record.granted
        return False

    def record(self, record: ConsentRecord) -> None:
        if record.purpose not in PURPOSES:
            raise ValueError(f"Unknown consent purpose '{record.purpose}'")
        self._records.append(record)

    def history(self, user_id: str) -> list[ConsentRecord]:
        return [r for r in self._records if r.user_id == user_id]

    def grant(self, user_id: str, purpose: str, guardian_user_id: str | None = None) -> None:
        self.record(
            ConsentRecord(
                user_id=user_id,
                purpose=purpose,
                granted=True,
                at=datetime.now(timezone.utc),
                guardian_user_id=guardian_user_id,
            )
        )

    def revoke(self, user_id: str, purpose: str) -> None:
        self.record(
            ConsentRecord(
                user_id=user_id,
                purpose=purpose,
                granted=False,
                at=datetime.now(timezone.utc),
            )
        )

    def clear(self) -> None:
        self._records.clear()


def require_consent(ledger: ConsentLedger, user_id: str, purpose: str) -> None:
    """Raise unless consent is held. The gate every audio path passes through."""
    if not ledger.has_consent(user_id, purpose):
        raise ConsentError(user_id, purpose)


@dataclass
class ConsentState:
    """A learner's current consents, for the UI to render honestly."""

    user_id: str
    granted: set[str] = field(default_factory=set)

    @classmethod
    def build(cls, ledger: ConsentLedger, user_id: str) -> ConsentState:
        return cls(
            user_id=user_id,
            granted={p for p in PURPOSES if ledger.has_consent(user_id, p)},
        )

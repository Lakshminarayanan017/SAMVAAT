"""Audio retention — Ethics rule E3, as enforced code.

    "Raw audio is deleted within 24 hours of feature extraction, unless the
     learner has given separate, explicit, independently revocable consent to
     contribute to the research corpus."

Retention here is a TTL stamped on the object at write time plus a job that
enforces it. It is not a sentence in a privacy policy, and it is not a promise
that someone remembers to keep.

Voice is biometric data. It is the most sensitive thing this product handles,
and for a disabled learner it is also identifying in a way that is very hard to
undo. The default is deletion; keeping anything requires a specific reason
attached to a specific consent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol


class RetentionReason(str, Enum):
    """Why an audio object is being kept, and therefore for how long.

    Every stored object carries one. An object with no reason cannot be written.
    """

    #: The processing window. Feature extraction, then gone.
    PROCESSING = "processing"
    #: The learner asked to keep it so a trainer can listen back.
    LEARNER_REVIEW = "learner_review"
    #: Separately consented contribution to the atypical-speech corpus.
    RESEARCH_CORPUS = "research_corpus"


#: Maximum lifetime per reason. PROCESSING is capped at the Ethics E3 figure and
#: must never be raised — a longer default would weaken the guarantee silently.
MAX_RETENTION: dict[RetentionReason, timedelta | None] = {
    RetentionReason.PROCESSING: timedelta(hours=24),
    RetentionReason.LEARNER_REVIEW: timedelta(days=30),
    #: Indefinite, but only while consent stands. Revocation deletes immediately,
    #: which is why this is None rather than a long duration.
    RetentionReason.RESEARCH_CORPUS: None,
}

#: The consent purpose each reason requires. Enforced at write time.
REQUIRED_CONSENT: dict[RetentionReason, str] = {
    RetentionReason.PROCESSING: "speech_processing",
    RetentionReason.LEARNER_REVIEW: "store_audio_for_review",
    RetentionReason.RESEARCH_CORPUS: "research_corpus",
}


@dataclass(frozen=True)
class AudioObject:
    """A stored audio artefact and the terms it is stored under."""

    key: str
    user_id: str
    reason: RetentionReason
    created_at: datetime
    expires_at: datetime | None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at


def expiry_for(reason: RetentionReason, created_at: datetime) -> datetime | None:
    lifetime = MAX_RETENTION[reason]
    return None if lifetime is None else created_at + lifetime


class AudioStore(Protocol):
    """The seam the S3/Supabase implementation fills in M17."""

    def put(self, obj: AudioObject) -> None: ...

    def get(self, key: str) -> AudioObject | None: ...

    def delete(self, key: str) -> bool: ...

    def list_all(self) -> list[AudioObject]: ...


class InMemoryAudioStore:
    """Development-only. Not persistent, and deliberately so.

    Losing every recording on restart is the correct failure mode for a store
    that has not yet had its retention job deployed.
    """

    def __init__(self) -> None:
        self._objects: dict[str, AudioObject] = {}

    def put(self, obj: AudioObject) -> None:
        self._objects[obj.key] = obj

    def get(self, key: str) -> AudioObject | None:
        return self._objects.get(key)

    def delete(self, key: str) -> bool:
        return self._objects.pop(key, None) is not None

    def list_all(self) -> list[AudioObject]:
        return list(self._objects.values())


@dataclass(frozen=True)
class PurgeResult:
    deleted: list[str]
    remaining: int

    @property
    def count(self) -> int:
        return len(self.deleted)


def purge_expired(store: AudioStore, now: datetime | None = None) -> PurgeResult:
    """Delete everything past its TTL.

    Run on a schedule. The test that proves it works is the one that matters in
    an audit, not this docstring.
    """
    now = now or datetime.now(timezone.utc)

    deleted = [obj.key for obj in store.list_all() if obj.is_expired(now)]
    for key in deleted:
        store.delete(key)

    return PurgeResult(deleted=deleted, remaining=len(store.list_all()))


def purge_for_user(
    store: AudioStore,
    user_id: str,
    reason: RetentionReason | None = None,
) -> PurgeResult:
    """Delete a learner's audio immediately.

    Called when consent is revoked and when a learner exercises erasure. If
    `reason` is given, only objects held under that reason are removed — so
    withdrawing research consent does not also destroy recordings the learner
    asked their trainer to review.
    """
    targets = [
        obj.key
        for obj in store.list_all()
        if obj.user_id == user_id and (reason is None or obj.reason is reason)
    ]
    for key in targets:
        store.delete(key)

    return PurgeResult(deleted=targets, remaining=len(store.list_all()))

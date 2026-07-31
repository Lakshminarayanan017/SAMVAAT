"""Audio retention and consent.

Named in the Ethics Charter as the test that enforces rule E3. These are the
tests that would be produced in an audit, so they assert the guarantee, not the
implementation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.security.consent import (
    ConsentError,
    InMemoryConsentLedger,
    require_consent,
)
from app.security.retention import (
    MAX_RETENTION,
    AudioObject,
    InMemoryAudioStore,
    RetentionReason,
    expiry_for,
    purge_expired,
    purge_for_user,
)
from tests.conftest import Learner

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


def consent(learner: Learner, purpose: str, granted: bool = True) -> None:
    response = learner.post(
        "/audio/consent", json={"purpose": purpose, "granted": granted}
    )
    assert response.status_code == 200, response.text


def upload(learner: Learner, reason: str = "processing"):
    return learner.post(
        "/audio/upload-url",
        json={
            "session_id": "s1",
            "block_id": "phrase.greetings.good_morning_01",
            "reason": reason,
            "duration_seconds": 3.2,
        },
    )


# ── Ethics E3: the 24-hour guarantee ─────────────────────────────────────────


class TestRetentionPolicy:
    def test_processing_audio_expires_within_twenty_four_hours(self) -> None:
        """The figure in Ethics E3, asserted rather than trusted."""
        expiry = expiry_for(RetentionReason.PROCESSING, NOW)

        assert expiry is not None
        assert expiry - NOW <= timedelta(hours=24)

    def test_the_processing_ceiling_cannot_be_raised_unnoticed(self) -> None:
        """A change to this constant must break a test, not weaken a promise."""
        assert MAX_RETENTION[RetentionReason.PROCESSING] == timedelta(hours=24)

    def test_research_audio_has_no_expiry_but_depends_on_consent(self) -> None:
        # Indefinite while consent stands — revocation deletes it, which is
        # tested separately. A long TTL would be the wrong model here.
        assert expiry_for(RetentionReason.RESEARCH_CORPUS, NOW) is None

    def test_purge_deletes_expired_audio_and_leaves_the_rest(self) -> None:
        store = InMemoryAudioStore()
        store.put(_obj("old", RetentionReason.PROCESSING, NOW - timedelta(hours=48)))
        store.put(_obj("fresh", RetentionReason.PROCESSING, NOW - timedelta(hours=1)))
        store.put(_obj("kept", RetentionReason.RESEARCH_CORPUS, NOW - timedelta(days=400)))

        result = purge_expired(store, NOW)

        assert result.deleted == ["old"]
        assert store.get("old") is None
        assert store.get("fresh") is not None
        assert store.get("kept") is not None

    def test_purge_is_idempotent(self) -> None:
        store = InMemoryAudioStore()
        store.put(_obj("old", RetentionReason.PROCESSING, NOW - timedelta(hours=48)))

        assert purge_expired(store, NOW).count == 1
        assert purge_expired(store, NOW).count == 0

    def test_erasure_removes_only_the_named_learner(self) -> None:
        store = InMemoryAudioStore()
        store.put(_obj("a", RetentionReason.PROCESSING, NOW, user="u1"))
        store.put(_obj("b", RetentionReason.PROCESSING, NOW, user="u2"))

        purge_for_user(store, "u1")

        assert store.get("a") is None
        assert store.get("b") is not None

    def test_withdrawing_research_consent_spares_review_recordings(self) -> None:
        """Withdrawing one consent must not destroy data held under another."""
        store = InMemoryAudioStore()
        store.put(_obj("research", RetentionReason.RESEARCH_CORPUS, NOW))
        store.put(_obj("review", RetentionReason.LEARNER_REVIEW, NOW))

        purge_for_user(store, "u1", RetentionReason.RESEARCH_CORPUS)

        assert store.get("research") is None
        assert store.get("review") is not None


# ── Consent enforcement ──────────────────────────────────────────────────────


class TestConsentLedger:
    def test_absence_of_a_record_is_absence_of_consent(self) -> None:
        ledger = InMemoryConsentLedger()
        assert ledger.has_consent("u1", "speech_processing") is False

    def test_grant_then_revoke_leaves_no_consent(self) -> None:
        ledger = InMemoryConsentLedger()
        ledger.grant("u1", "speech_processing")
        assert ledger.has_consent("u1", "speech_processing") is True

        ledger.revoke("u1", "speech_processing")
        assert ledger.has_consent("u1", "speech_processing") is False

    def test_history_is_append_only(self) -> None:
        """'When did this learner consent, and to what' must be answerable later."""
        ledger = InMemoryConsentLedger()
        ledger.grant("u1", "research_corpus")
        ledger.revoke("u1", "research_corpus")

        assert len(ledger.history("u1")) == 2

    def test_purposes_are_independent(self) -> None:
        ledger = InMemoryConsentLedger()
        ledger.grant("u1", "speech_processing")

        assert ledger.has_consent("u1", "speech_processing") is True
        assert ledger.has_consent("u1", "research_corpus") is False

    def test_an_unknown_purpose_is_rejected_rather_than_silently_false(self) -> None:
        with pytest.raises(ValueError, match="Unknown consent purpose"):
            InMemoryConsentLedger().has_consent("u1", "sell_to_advertisers")

    def test_require_consent_raises_when_absent(self) -> None:
        with pytest.raises(ConsentError):
            require_consent(InMemoryConsentLedger(), "u1", "speech_processing")


# ── The gate, end to end ─────────────────────────────────────────────────────


class TestUploadEndpoint:
    def test_recording_without_consent_is_refused(self, learner: Learner) -> None:
        response = upload(learner)

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "consent_required"

    def test_the_refusal_is_written_for_a_learner_not_a_lawyer(
        self, learner: Learner
    ) -> None:
        message = upload(learner).json()["detail"]["message"]
        assert "permission" in message.lower()

    def test_consented_upload_returns_a_ticket_with_an_expiry(self, learner: Learner) -> None:
        consent(learner, "speech_processing")
        body = upload(learner).json()

        assert body["key"].startswith("audio/")
        assert body["expires_at"] is not None
        assert body["reason"] == "processing"

    def test_the_learner_is_told_how_long_their_voice_is_kept(
        self, learner: Learner
    ) -> None:
        """They are entitled to know, in words, at the moment they record."""
        consent(learner, "speech_processing")
        notice = upload(learner).json()["retention_notice"]

        assert "24 hours" in notice
        assert "deleted" in notice

    def test_research_storage_needs_its_own_separate_consent(
        self, learner: Learner
    ) -> None:
        consent(learner, "speech_processing")

        refused = upload(learner, reason="research_corpus")
        assert refused.status_code == 403
        assert refused.json()["detail"]["purpose"] == "research_corpus"

        consent(learner, "research_corpus")
        assert upload(learner, reason="research_corpus").status_code == 200

    def test_revoking_consent_deletes_immediately(self, learner: Learner) -> None:
        """Consent you can withdraw without the data going too is not consent."""
        consent(learner, "speech_processing")
        consent(learner, "research_corpus")
        upload(learner, reason="research_corpus")

        assert len(learner.get("/audio/mine").json()) == 1

        consent(learner, "research_corpus", granted=False)

        assert learner.get("/audio/mine").json() == []

    def test_revoking_speech_processing_deletes_everything(self, learner: Learner) -> None:
        consent(learner, "speech_processing")
        upload(learner)
        upload(learner)
        assert len(learner.get("/audio/mine").json()) == 2

        consent(learner, "speech_processing", granted=False)
        assert learner.get("/audio/mine").json() == []

    def test_erasure_endpoint_removes_a_learners_audio(self, learner: Learner) -> None:
        consent(learner, "speech_processing")
        upload(learner)

        body = learner.delete("/audio/me").json()

        assert body["deleted"] == 1
        assert body["remaining"] == 0
        assert learner.get("/audio/mine").json() == []

    def test_purge_endpoint_clears_expired_objects(self, learner: Learner) -> None:
        """The scheduled retention job, exercised through the same code path."""
        consent(learner, "speech_processing")
        upload(learner)

        # Nothing is expired yet, so the purge must be a no-op rather than a
        # blanket delete.
        assert learner.post("/audio/purge").json()["deleted"] == 0
        assert len(learner.get("/audio/mine").json()) == 1

    def test_consents_are_reported_back_to_the_learner(self, learner: Learner) -> None:
        consent(learner, "speech_processing")
        body = learner.get("/audio/consent").json()

        assert "speech_processing" in body["granted"]
        assert "research_corpus" not in body["granted"]
        assert "research_corpus" in body["available"]

    def test_learners_consents_do_not_leak_across_users(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        """One learner consenting must not let another record."""
        consent(learner, "speech_processing")
        assert upload(other_learner).status_code == 403

    def test_a_learner_only_sees_their_own_recordings(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        consent(learner, "speech_processing")
        upload(learner)

        assert len(learner.get("/audio/mine").json()) == 1
        assert other_learner.get("/audio/mine").json() == []


def _obj(
    key: str,
    reason: RetentionReason,
    created_at: datetime,
    user: str = "u1",
) -> AudioObject:
    return AudioObject(
        key=key,
        user_id=user,
        reason=reason,
        created_at=created_at,
        expires_at=expiry_for(reason, created_at),
    )

"""Audio retention and consent.

Named in the Ethics Charter as the test that enforces rule E3. These are the
tests that would be produced in an audit, so they assert the guarantee, not the
implementation.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import audio
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

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clean_state() -> None:
    audio._store = InMemoryAudioStore()
    audio._ledger = InMemoryConsentLedger()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def consent(client: TestClient, purpose: str, granted: bool = True, user: str = "u1") -> None:
    response = client.post(
        "/audio/consent",
        json={"user_id": user, "purpose": purpose, "granted": granted},
    )
    assert response.status_code == 200, response.text


def upload(client: TestClient, reason: str = "processing", user: str = "u1"):
    return client.post(
        "/audio/upload-url",
        json={
            "user_id": user,
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
    def test_recording_without_consent_is_refused(self, client: TestClient) -> None:
        response = upload(client)

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "consent_required"

    def test_the_refusal_is_written_for_a_learner_not_a_lawyer(
        self, client: TestClient
    ) -> None:
        message = upload(client).json()["detail"]["message"]
        assert "permission" in message.lower()

    def test_consented_upload_returns_a_ticket_with_an_expiry(self, client: TestClient) -> None:
        consent(client, "speech_processing")
        body = upload(client).json()

        assert body["key"].startswith("audio/")
        assert body["expires_at"] is not None
        assert body["reason"] == "processing"

    def test_the_learner_is_told_how_long_their_voice_is_kept(
        self, client: TestClient
    ) -> None:
        """They are entitled to know, in words, at the moment they record."""
        consent(client, "speech_processing")
        notice = upload(client).json()["retention_notice"]

        assert "24 hours" in notice
        assert "deleted" in notice

    def test_research_storage_needs_its_own_separate_consent(
        self, client: TestClient
    ) -> None:
        consent(client, "speech_processing")

        refused = upload(client, reason="research_corpus")
        assert refused.status_code == 403
        assert refused.json()["detail"]["purpose"] == "research_corpus"

        consent(client, "research_corpus")
        assert upload(client, reason="research_corpus").status_code == 200

    def test_revoking_consent_deletes_immediately(self, client: TestClient) -> None:
        """Consent you can withdraw without the data going too is not consent."""
        consent(client, "speech_processing")
        consent(client, "research_corpus")
        upload(client, reason="research_corpus")

        assert len(audio._store.list_all()) == 1

        consent(client, "research_corpus", granted=False)

        assert audio._store.list_all() == []

    def test_revoking_speech_processing_deletes_everything(self, client: TestClient) -> None:
        consent(client, "speech_processing")
        upload(client)
        upload(client)
        assert len(audio._store.list_all()) == 2

        consent(client, "speech_processing", granted=False)
        assert audio._store.list_all() == []

    def test_erasure_endpoint_removes_a_learners_audio(self, client: TestClient) -> None:
        consent(client, "speech_processing")
        upload(client)

        body = client.delete("/audio/user/u1").json()

        assert body["deleted"] == 1
        assert body["remaining"] == 0

    def test_purge_endpoint_clears_expired_objects(self, client: TestClient) -> None:
        consent(client, "speech_processing")
        upload(client)

        # Age the object past its TTL.
        stored = audio._store.list_all()[0]
        audio._store.put(
            AudioObject(
                key=stored.key,
                user_id=stored.user_id,
                reason=stored.reason,
                created_at=stored.created_at - timedelta(days=2),
                expires_at=stored.expires_at - timedelta(days=2),  # type: ignore[operator]
            )
        )

        assert client.post("/audio/purge").json()["deleted"] == 1

    def test_consents_are_reported_back_to_the_learner(self, client: TestClient) -> None:
        consent(client, "speech_processing")
        body = client.get("/audio/consent/u1").json()

        assert "speech_processing" in body["granted"]
        assert "research_corpus" not in body["granted"]
        assert "research_corpus" in body["available"]

    def test_learners_consents_do_not_leak_across_users(self, client: TestClient) -> None:
        consent(client, "speech_processing", user="u1")
        assert upload(client, user="u2").status_code == 403


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

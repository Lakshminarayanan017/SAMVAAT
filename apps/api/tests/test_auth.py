"""Identity, sessions and isolation.

The regression these guard against is the one this module was written to fix:
until M1, every endpoint took `user_id` from the request body, so anyone could
read anyone's rehearsed interview answers by guessing an id.

For this product that is not an abstract severity rating. The data is a disabled
person's practice attempts at disclosing their disability to an employer.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.security.auth import ALGORITHM, decode_token, issue_token, new_user_id
from tests.conftest import Learner

#: Every route that touches a learner's own data.
PROTECTED = [
    ("post", "/practice/session", {}),
    ("post", "/practice/review", {"block_id": "x", "correct": True}),
    ("post", "/audio/upload-url", {"session_id": "s", "block_id": "b", "duration_seconds": 1}),
    ("get", "/audio/consent", None),
    ("get", "/audio/mine", None),
    ("post", "/interview/start", {}),
    ("get", "/interviews", None),
    ("get", "/auth/me", None),
]


class TestTokens:
    def test_a_token_round_trips(self) -> None:
        principal = decode_token(issue_token("usr_1", role="trainer", is_guest=False))

        assert principal.user_id == "usr_1"
        assert principal.role == "trainer"
        assert principal.is_guest is False

    def test_an_expired_token_is_refused(self) -> None:
        settings = get_settings()
        past = datetime.now(timezone.utc) - timedelta(days=1)
        expired = jwt.encode(
            {"sub": "usr_1", "iat": past, "exp": past, "iss": settings.service_name},
            settings.jwt_secret,
            algorithm=ALGORITHM,
        )

        with pytest.raises(Exception) as caught:
            decode_token(expired)
        assert caught.value.status_code == 401

    @pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
    def test_a_token_signed_with_another_key_is_refused(self) -> None:
        forged = jwt.encode(
            {
                "sub": "usr_victim",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(days=1),
                "iss": get_settings().service_name,
            },
            "not-our-signing-key",
            algorithm=ALGORITHM,
        )

        with pytest.raises(Exception) as caught:
            decode_token(forged)
        assert caught.value.status_code == 401

    @pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
    def test_expiry_and_forgery_give_the_same_message(self) -> None:
        """Distinguishing them tells an attacker which of the two they achieved."""
        settings = get_settings()
        past = datetime.now(timezone.utc) - timedelta(days=1)

        expired = jwt.encode(
            {"sub": "u", "iat": past, "exp": past, "iss": settings.service_name},
            settings.jwt_secret,
            algorithm=ALGORITHM,
        )
        forged = jwt.encode({"sub": "u"}, "wrong-key", algorithm=ALGORITHM)

        messages = []
        for token in (expired, forged):
            with pytest.raises(Exception) as caught:
                decode_token(token)
            messages.append(caught.value.detail["message"])

        assert messages[0] == messages[1]

    def test_garbage_is_refused_rather_than_crashing(self) -> None:
        with pytest.raises(Exception) as caught:
            decode_token("not-a-jwt-at-all")
        assert caught.value.status_code == 401


class TestGuestFirst:
    def test_anyone_can_start_without_an_account(self, anonymous: TestClient) -> None:
        """Someone deciding whether to trust us should be able to practise
        before handing over an email."""
        body = anonymous.post("/auth/guest").json()

        assert body["is_guest"] is True
        assert body["access_token"]
        assert body["needs_onboarding"] is True

    def test_two_guests_are_different_people(self, anonymous: TestClient) -> None:
        first = anonymous.post("/auth/guest").json()["user_id"]
        second = anonymous.post("/auth/guest").json()["user_id"]
        assert first != second

    def test_signing_up_keeps_everything_practised_as_a_guest(
        self, learner: Learner
    ) -> None:
        """Losing a week of practice would punish exactly the caution we wanted
        to allow."""
        learner.post("/audio/consent", json={"purpose": "speech_processing", "granted": True})

        upgraded = learner.post(
            "/auth/upgrade", json={"email": "ravi@example.com"}
        ).json()

        assert upgraded["is_guest"] is False
        assert upgraded["user_id"] == learner.user_id

        # Same person, so the consent survives.
        still = learner.get("/audio/consent").json()
        assert "speech_processing" in still["granted"]

    def test_an_email_cannot_be_claimed_twice(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        learner.post("/auth/upgrade", json={"email": "taken@example.com"})
        response = other_learner.post("/auth/upgrade", json={"email": "taken@example.com"})

        assert response.status_code == 409
        assert "sign in" in response.json()["detail"]["message"].lower()


class TestEveryRouteRequiresAToken:
    @pytest.mark.parametrize(("method", "path", "payload"), PROTECTED)
    def test_no_token_is_refused(
        self, anonymous: TestClient, method: str, path: str, payload: dict | None
    ) -> None:
        call = getattr(anonymous, method)
        response = call(path, json=payload) if payload is not None else call(path)

        assert response.status_code == 401, f"{method.upper()} {path} allowed an anonymous caller"

    @pytest.mark.parametrize(("method", "path", "payload"), PROTECTED)
    def test_a_junk_token_is_refused(
        self, anonymous: TestClient, method: str, path: str, payload: dict | None
    ) -> None:
        headers = {"Authorization": "Bearer obviously-not-valid"}
        call = getattr(anonymous, method)
        response = (
            call(path, json=payload, headers=headers)
            if payload is not None
            else call(path, headers=headers)
        )

        assert response.status_code == 401

    def test_the_refusal_is_written_for_a_learner(self, anonymous: TestClient) -> None:
        message = anonymous.get("/auth/me").json()["detail"]["message"]

        assert "sign in" in message.lower()
        for word in ("token", "jwt", "unauthorized", "credentials", "401"):
            assert word not in message.lower()


class TestIsolation:
    """The IDOR regression suite. Each of these was possible before M1."""

    def test_one_learner_cannot_read_anothers_interview(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        from app.routers import conversation

        class Stub:
            async def interview_start(self, interview_id, *args, **kwargs):
                return {
                    "block": {"id": "q1", "canonical_text": "Tell me about yourself."},
                    "state": {"interview_id": interview_id},
                    "generated": False,
                    "provider": "scripted",
                    "finished": False,
                    "progress": "Question 1 of about 10",
                }

        conversation._client = Stub()  # type: ignore[assignment]

        cid = learner.post("/interview/start", json={}).json()["conversation_id"]

        assert other_learner.get(f"/interview/{cid}").status_code == 404

    def test_one_learner_cannot_read_anothers_consents(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        learner.post("/audio/consent", json={"purpose": "research_corpus", "granted": True})

        assert other_learner.get("/audio/consent").json()["granted"] == []

    def test_one_learner_cannot_read_anothers_recordings(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        learner.post("/audio/consent", json={"purpose": "speech_processing", "granted": True})
        learner.post(
            "/audio/upload-url",
            json={"session_id": "s", "block_id": "b", "duration_seconds": 1},
        )

        assert other_learner.get("/audio/mine").json() == []

    def test_a_valid_token_for_a_nonexistent_user_conjures_nothing(
        self, anonymous: TestClient, forged_token: str
    ) -> None:
        """A good signature is not the same as an existing learner."""
        headers = {"Authorization": f"Bearer {forged_token}"}

        assert anonymous.get("/auth/me", headers=headers).status_code == 401
        assert anonymous.get("/interviews", headers=headers).json() == []


class TestPersistence:
    """The other red gap: state used to vanish on restart."""

    def test_progress_survives_a_new_client(self, app, learner: Learner) -> None:
        block_id = learner.post(
            "/practice/session", json={"session_length_target_min": 5}
        ).json()["items"][0]["block_id"]

        learner.post("/practice/review", json={"block_id": block_id, "correct": True})

        # A completely new client and connection, same database and same token.
        with TestClient(app) as fresh:
            later = fresh.post(
                "/practice/session",
                json={"session_length_target_min": 30},
                headers=learner.headers,
            ).json()

        seen = {item["block_id"]: item for item in later["items"]}
        if block_id in seen:
            assert seen[block_id]["is_new"] is False


class TestErasure:
    def test_a_learner_can_delete_everything_themselves(self, learner: Learner) -> None:
        """A right that requires emailing somebody is not a right a disabled
        learner can reliably exercise."""
        learner.post("/audio/consent", json={"purpose": "speech_processing", "granted": True})
        learner.post(
            "/audio/upload-url",
            json={"session_id": "s", "block_id": "b", "duration_seconds": 1},
        )

        body = learner.delete("/auth/me").json()
        assert body["erased"] is True

        # The token still verifies, but there is no longer anyone behind it.
        assert learner.get("/auth/me").status_code == 401

    def test_erasure_does_not_touch_anyone_else(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        other_learner.post(
            "/audio/consent", json={"purpose": "speech_processing", "granted": True}
        )

        learner.delete("/auth/me")

        assert other_learner.get("/auth/me").status_code == 200
        assert "speech_processing" in other_learner.get("/audio/consent").json()["granted"]


def test_a_generated_user_id_marks_whether_it_is_a_guest() -> None:
    assert new_user_id(guest=True).startswith("gst_")
    assert new_user_id(guest=False).startswith("usr_")

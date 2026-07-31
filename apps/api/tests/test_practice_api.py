"""Practice endpoints, exercised against the real 226-phrase bank."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.learning.repository import InMemoryCardRepository
from app.main import create_app
from app.routers import practice


@pytest.fixture(autouse=True)
def clean_repository() -> None:
    """Each test starts with an empty learner. State is per-process, not per-test."""
    practice._repository = InMemoryCardRepository()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def session(client: TestClient, **overrides) -> dict:
    payload = {"user_id": "u1", "session_length_target_min": 5, "input_mode": "text"}
    payload.update(overrides)
    response = client.post("/practice/session", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


class TestSession:
    def test_a_new_learner_gets_a_session_of_new_material(self, client: TestClient) -> None:
        body = session(client)

        assert body["items"]
        assert all(item["is_new"] for item in body["items"])
        assert body["estimated_seconds"] > 0

    def test_new_material_is_introduced_easiest_first(self, client: TestClient) -> None:
        difficulties = [item["difficulty"] for item in session(client)["items"]]
        # The opening item may be reordered to a likely win, so compare the rest.
        assert difficulties[1:] == sorted(difficulties[1:])

    def test_session_length_is_respected(self, client: TestClient) -> None:
        short = session(client, session_length_target_min=3)
        long_ = session(client, session_length_target_min=20)
        assert len(long_["items"]) > len(short["items"])

    def test_slower_input_modes_get_fewer_items_not_a_rushed_session(
        self, client: TestClient
    ) -> None:
        text = session(client, input_mode="text")
        switch = session(client, input_mode="switch")

        assert len(switch["items"]) < len(text["items"])
        # Both still aim at roughly the same five minutes.
        assert abs(text["estimated_seconds"] - switch["estimated_seconds"]) < 150

    def test_easy_read_profiles_get_a_lighter_session(self, client: TestClient) -> None:
        normal = session(client)
        easy_read = session(client, one_step_per_screen=True)
        assert len(easy_read["items"]) < len(normal["items"])

    def test_can_be_filtered_to_a_scenario(self, client: TestClient) -> None:
        body = session(client, scenario_tags=["interview"], session_length_target_min=20)

        assert body["items"]
        assert all("interview" in item["block_id"] for item in body["items"])

    def test_an_unknown_scenario_says_so_rather_than_failing(self, client: TestClient) -> None:
        body = session(client, scenario_tags=["no-such-category"])
        assert body["items"] == []
        assert body["note"]


class TestReview:
    def test_recording_a_review_schedules_the_next_one(self, client: TestClient) -> None:
        block_id = session(client)["items"][0]["block_id"]

        response = client.post(
            "/practice/review",
            json={"user_id": "u1", "block_id": block_id, "correct": True},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["grade_label"] == "Good"
        assert body["interval_days"] >= 1
        assert body["reps"] == 1

    def test_a_reviewed_card_is_no_longer_new(self, client: TestClient) -> None:
        block_id = session(client)["items"][0]["block_id"]
        client.post(
            "/practice/review",
            json={"user_id": "u1", "block_id": block_id, "correct": True},
        )

        later = session(client, session_length_target_min=30)["items"]
        seen = {item["block_id"]: item for item in later}
        if block_id in seen:
            assert seen[block_id]["is_new"] is False

    def test_learners_are_isolated_from_each_other(self, client: TestClient) -> None:
        block_id = session(client)["items"][0]["block_id"]
        client.post(
            "/practice/review",
            json={"user_id": "u1", "block_id": block_id, "correct": True},
        )

        other = session(client, user_id="u2")
        assert all(item["is_new"] for item in other["items"])

    def test_unknown_phrase_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/practice/review",
            json={"user_id": "u1", "block_id": "phrase.nope.nope_01", "correct": True},
        )
        assert response.status_code == 404

    def test_a_wrong_answer_comes_back_sooner_than_a_right_one(self, client: TestClient) -> None:
        items = session(client, session_length_target_min=20)["items"]
        right, wrong = items[0]["block_id"], items[1]["block_id"]

        good = client.post(
            "/practice/review", json={"user_id": "u1", "block_id": right, "correct": True}
        ).json()
        again = client.post(
            "/practice/review", json={"user_id": "u1", "block_id": wrong, "correct": False}
        ).json()

        assert again["interval_days"] <= good["interval_days"]
        assert again["lapses"] == 1

    def test_an_unreliable_transcription_is_not_held_against_the_learner(
        self, client: TestClient
    ) -> None:
        """An ASR weakness must never surface as the learner's weakness."""
        block_id = session(client)["items"][0]["block_id"]

        body = client.post(
            "/practice/review",
            json={
                "user_id": "u1",
                "block_id": block_id,
                "correct": False,
                "low_confidence_input": True,
            },
        ).json()

        assert body["grade_label"] != "Again"
        assert body["lapses"] == 0
        assert "does not count against you" in body["message"]

    def test_the_review_endpoint_accepts_no_timing_field(self, client: TestClient) -> None:
        """Ethics E6, enforced at the API boundary as well as in the grader."""
        fields = practice.ReviewRequest.model_fields
        for banned in ("duration", "latency", "elapsed", "seconds", "response_time"):
            assert not any(banned in name for name in fields), f"ReviewRequest exposes '{banned}'"

    def test_feedback_never_tells_a_learner_they_failed(self, client: TestClient) -> None:
        """The Ethics Charter copy rules apply to the string learners read most."""
        block_id = session(client)["items"][0]["block_id"]

        message = client.post(
            "/practice/review",
            json={"user_id": "u1", "block_id": block_id, "correct": False},
        ).json()["message"]

        assert not any(word in message.lower() for word in ("wrong", "fail", "incorrect", "error"))
        assert "not quite yet" in message.lower()


class TestFullLoop:
    def test_learn_forget_relearn(self, client: TestClient) -> None:
        """The loop that matters: an item learned, lapsed, and recovered.

        These reviews all land in the same instant, as they would if a learner
        retried an item within one session. FSRS deliberately grants little or no
        stability for that: `exp(w10 * (1 - R)) - 1` goes to zero as
        retrievability approaches 1, because answering something you have not had
        time to forget is not evidence you will remember it next week.

        So this test pins the bookkeeping — reps, lapses, and that a lapse pulls
        the item back sooner — rather than expecting intervals to grow within a
        single session. Interval growth over real elapsed time is covered by
        test_learning.py::test_repeated_success_lengthens_the_interval.
        """
        block_id = session(client)["items"][0]["block_id"]

        def review(correct: bool) -> dict:
            return client.post(
                "/practice/review",
                json={"user_id": "u1", "block_id": block_id, "correct": correct},
            ).json()

        first = review(True)
        assert first["reps"] == 1 and first["lapses"] == 0

        second = review(True)
        assert second["reps"] == 2
        assert second["interval_days"] >= first["interval_days"]

        lapsed = review(False)
        assert lapsed["lapses"] == 1
        assert lapsed["interval_days"] < second["interval_days"]

        recovered = review(True)
        assert recovered["reps"] == 4
        assert recovered["lapses"] == 1
        # Recovery does not undo the lapse: the item stays in the short queue
        # until the learner gets it right after real time has passed.
        assert recovered["interval_days"] >= lapsed["interval_days"]

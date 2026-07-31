"""Role-play and mock-interview endpoints.

The GenAI service is stubbed here. That is deliberate: these tests are about the
gateway's own responsibilities — owning conversation state, isolating learners,
persisting the audit record, and degrading honestly — none of which should
depend on an LLM being reachable.

The GenAI service's own behaviour is tested in services/genai.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.routers import conversation
from app.services.genai_client import GenAiUnavailable
from tests.conftest import Learner


class StubGenAi:
    """A GenAI service that works, unless told otherwise."""

    def __init__(self) -> None:
        self.fail = False
        self.calls: list[str] = []

    def _guard(self, name: str) -> None:
        self.calls.append(name)
        if self.fail:
            raise GenAiUnavailable(f"stubbed outage on {name}")

    async def scenarios(self) -> list[dict]:
        self._guard("scenarios")
        return [{"id": "first_day", "title": "Your first day", "role": "supervisor"}]

    async def open_roleplay(self, scenario_id: str, difficulty: int, persona: str) -> dict:
        self._guard("open_roleplay")
        return {
            "block": {"id": "scenario.turn.1", "canonical_text": "Good morning. You must be new?"},
            "state": {"scenario_id": scenario_id, "turn_number": 0, "goal_met": False},
            "generated": False,
            "provider": "scripted",
        }

    async def roleplay_respond(self, state, learner_text, met_expectation, text_complexity) -> dict:
        self._guard("roleplay_respond")
        turn = state.get("turn_number", 0) + 1
        return {
            "block": {"id": f"scenario.turn.{turn}", "canonical_text": "Good to meet you."},
            "state": {**state, "turn_number": turn, "goal_met": turn >= 3},
            "generated": False,
            "provider": "scripted",
        }

    async def interview_start(self, interview_id, track, persona, target_questions, job_context):
        self._guard("interview_start")
        return {
            "block": {"id": "interview.hr.q1", "canonical_text": "Tell me about yourself."},
            "state": {"interview_id": interview_id, "track": track, "status": "in_progress"},
            "generated": False,
            "provider": "scripted",
            "finished": False,
            "progress": "Question 1 of about 10",
        }

    async def interview_next(self, state, answer) -> dict:
        self._guard("interview_next")
        asked = state.get("asked", 1) + 1
        finished = asked > 3
        return {
            "block": {"id": f"interview.hr.q{asked}", "canonical_text": "And your strengths?"},
            "state": {**state, "asked": asked},
            "generated": False,
            "provider": "scripted",
            "finished": finished,
            "progress": f"Question {asked} of about 10",
        }

    async def interview_pause(self, state) -> dict:
        self._guard("interview_pause")
        return {"state": {**state, "status": "paused"}, "message": "Paused."}

    async def score(self, question, answer, role_context) -> dict:
        self._guard("score")
        return {
            "scored": True,
            "dimensions": [{"name": "content_relevance", "score": 4}],
            "strengths": ["You gave a concrete example."],
            "improvements": ["Add the result at the end."],
            "audit": {
                "rubric_version": "rubric-v1",
                "scored_dimensions": ["content_relevance"],
                "excluded_dimensions": ["speech_rate", "articulation_quality"],
                "prompt_hash": "abc123",
                "model_id": "scripted",
            },
        }

    async def disclosure(self, step: str) -> dict:
        self._guard("disclosure")
        return {"step": step, "prompts": ["What helps you work well?"]}

    async def story(self, job_context, situation, reading_level, has_trainer) -> dict:
        self._guard("story")
        return {"title": "My first day", "panels": [], "status": "draft", "generated": False}


@pytest.fixture(autouse=True)
def stub() -> Iterator[StubGenAi]:
    fake = StubGenAi()
    conversation._client = fake  # type: ignore[assignment]
    yield fake


def start_interview(learner: Learner) -> dict:
    response = learner.post("/interview/start", json={"track": "hr"})
    assert response.status_code == 200, response.text
    return response.json()


class TestRoleplay:
    def test_opening_a_scenario_creates_a_conversation(self, learner: Learner) -> None:
        body = learner.post(
            "/roleplay/start", json={"scenario_id": "first_day"}
        ).json()

        assert body["conversation_id"].startswith("rp_")
        assert body["block"]["canonical_text"]

    def test_a_turn_advances_the_stored_state(self, learner: Learner) -> None:
        """The gateway owns state, so it must survive between requests — the
        GenAI service keeps none of it."""
        opened = learner.post(
            "/roleplay/start", json={"scenario_id": "first_day"}
        ).json()
        cid = opened["conversation_id"]

        def turn(text: str) -> dict:
            payload = {"text": text}
            return learner.post(f"/roleplay/{cid}/reply", json=payload).json()

        first = turn("Hello")
        second = turn("I am new")

        assert first["block"]["id"] == "scenario.turn.1"
        assert second["block"]["id"] == "scenario.turn.2"

    def test_reaching_the_goal_finishes_the_conversation(self, learner: Learner) -> None:
        cid = learner.post(
            "/roleplay/start", json={"scenario_id": "first_day"}
        ).json()["conversation_id"]

        for _ in range(3):
            body = learner.post(
                f"/roleplay/{cid}/reply", json={"text": "ok"}
            ).json()

        assert body["finished"] is True

    def test_a_learner_cannot_reply_into_someone_elses_conversation(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        """The whole reason identity moved out of the request body."""
        cid = learner.post(
            "/roleplay/start", json={"scenario_id": "first_day"}
        ).json()["conversation_id"]

        response = other_learner.post(f"/roleplay/{cid}/reply", json={"text": "hi"})
        assert response.status_code == 404

    def test_an_unknown_conversation_is_indistinguishable_from_someone_elses(
        self, learner: Learner
    ) -> None:
        """Both 404, so conversation ids cannot be probed for existence."""
        assert learner.post(
            "/roleplay/rp_doesnotexist/reply", json={"text": "hi"}
        ).status_code == 404


class TestInterview:
    def test_starting_returns_the_first_question_and_progress(self, learner: Learner) -> None:
        body = start_interview(learner)

        assert body["block"]["canonical_text"]
        assert body["progress"] == "Question 1 of about 10"

    def test_progress_is_never_a_countdown(self, learner: Learner) -> None:
        """Ethics E6. 'Question 4 of about 10' is orientation; '6 remaining' or
        a timer is pressure, and pressure is what excludes P3, P4 and P5."""
        body = start_interview(learner)

        lowered = body["progress"].lower()
        for word in ("remaining", "left", "seconds", "minutes", "hurry", "time"):
            assert word not in lowered

    def test_answering_advances_to_the_next_question(self, learner: Learner) -> None:
        cid = start_interview(learner)["conversation_id"]

        body = learner.post(
            f"/interview/{cid}/answer", json={"answer": "I am consistent."}
        ).json()

        assert body["block"]["id"] == "interview.hr.q2"

    def test_an_interview_can_be_paused_and_resumed(self, learner: Learner) -> None:
        """Ethics E6. A learner with fatigue or anxiety must be able to stop at
        question four and come back tomorrow."""
        cid = start_interview(learner)["conversation_id"]
        learner.post(f"/interview/{cid}/answer", json={"answer": "first"})

        paused = learner.post(f"/interview/{cid}/pause", json={}).json()
        assert paused["status"] == "paused"

        resumed = learner.get(f"/interview/{cid}", params={}).json()
        assert len(resumed["exchanges"]) == 1
        assert resumed["finished"] is False

    def test_pausing_works_even_when_genai_is_down(
        self, learner: Learner, stub: StubGenAi
    ) -> None:
        """The one operation that must never fail. The state is already ours;
        marking it paused needs nobody's help."""
        cid = start_interview(learner)["conversation_id"]
        stub.fail = True

        response = learner.post(f"/interview/{cid}/pause", json={})

        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_a_finished_interview_rejects_further_answers(self, learner: Learner) -> None:
        cid = start_interview(learner)["conversation_id"]
        for _ in range(4):
            learner.post(f"/interview/{cid}/answer", json={"answer": "a"})

        response = learner.post(f"/interview/{cid}/answer", json={"answer": "a"})
        assert response.status_code == 409

    def test_learners_only_see_their_own_interviews(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        start_interview(learner)
        start_interview(other_learner)

        assert len(learner.get("/interviews").json()) == 1
        assert len(other_learner.get("/interviews").json()) == 1


class TestScoring:
    def test_a_score_persists_an_audit_record(self, learner: Learner) -> None:
        """Layer four of the E2 enforcement. The GenAI service proves the rubric
        was blind to speech traits; storing the record is what makes that
        provable later, to someone who was not in the room."""
        body = learner.post(
            "/interview/score",
            json={"question": "Your strengths?", "answer": "I am careful."},
        ).json()

        assert body["scored"] is True
        assert body["audit_id"]

        record = learner.get(f"/interview/audit/{body['audit_id']}").json()
        assert record["rubric_version"] == "rubric-v1"
        assert "speech_rate" in record["excluded_dimensions"]
        assert "articulation_quality" in record["excluded_dimensions"]

    def test_feedback_leads_with_strengths(self, learner: Learner) -> None:
        body = learner.post(
            "/interview/score",
            json={"question": "q", "answer": "a"},
        ).json()

        assert body["strengths"]
        # Ethics Charter copy rules: at most two improvement points per session.
        assert len(body["improvements"]) <= 2

    def test_an_unknown_audit_id_is_a_404(self, learner: Learner) -> None:
        assert learner.get("/interview/audit/aud_nope").status_code == 404


class TestHonestDegradation:
    @pytest.fixture(autouse=True)
    def down(self, stub: StubGenAi) -> None:
        stub.fail = True

    @pytest.mark.parametrize(
        ("method", "path", "payload"),
        [
            ("post", "/roleplay/start", {"scenario_id": "first_day"}),
            ("post", "/interview/start", {}),
            ("post", "/interview/score", {"question": "q", "answer": "a"}),
            ("post", "/stories", {"job_context": "packing", "situation": "day 1"}),
        ],
    )
    def test_an_outage_returns_503_not_an_empty_success(
        self, learner: Learner, method: str, path: str, payload: dict
    ) -> None:
        """A learner staring at a blank screen cannot tell 'the service is down'
        from 'I did something wrong', and will assume the latter."""
        response = getattr(learner, method)(path, json=payload)

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "genai_unavailable"

    def test_the_outage_message_points_at_what_still_works(self, learner: Learner) -> None:
        body = learner.post("/interview/start", json={}).json()
        message = body["detail"]["message"]

        assert "still works" in message.lower()
        for word in ("error", "failed", "exception", "500"):
            assert word not in message.lower()

    def test_a_failed_turn_leaves_the_conversation_replayable(
        self, learner: Learner, stub: StubGenAi
    ) -> None:
        """Losing your place because a host went to sleep would be a cruel way
        to end a conversation someone found hard to start."""
        stub.fail = False
        cid = learner.post(
            "/roleplay/start", json={"scenario_id": "first_day"}
        ).json()["conversation_id"]

        stub.fail = True
        blocked = learner.post(f"/roleplay/{cid}/reply", json={"text": "hi"})
        assert blocked.status_code == 503

        stub.fail = False
        recovered = learner.post(f"/roleplay/{cid}/reply", json={"text": "hi"})
        assert recovered.status_code == 200
        assert recovered.json()["block"]["id"] == "scenario.turn.1"


class TestReadiness:
    def test_readyz_reports_speech_and_genai_separately(self, learner: Learner) -> None:
        """'Something is unhealthy' is not a diagnosis."""
        names = {d["name"] for d in learner.get("/readyz").json()["dependencies"]}
        assert names == {"speech", "genai"}

"""The trainer dashboard, and Ethics E5.

Two things are being proved here, and only one of them is a feature.

The feature is a cohort view. The other is that a trainer being *responsible*
for a learner and being *allowed to see their data* are separate facts, and only
the second is the learner's to give. Every test that looks like a permissions
test is really about that.
"""

from __future__ import annotations

import pytest

from tests.conftest import Learner, Trainer


def share(learner: Learner, granted: bool = True) -> None:
    """The learner's own decision to let their trainer see their progress."""
    response = learner.post(
        "/audio/consent", json={"purpose": "trainer_visibility", "granted": granted}
    )
    assert response.status_code == 200, response.text


def practise(learner: Learner) -> str:
    """One review, so there is something for a trainer to look at."""
    block_id = learner.post(
        "/practice/session", json={"session_length_target_min": 5}
    ).json()["items"][0]["block_id"]
    learner.post("/practice/review", json={"block_id": block_id, "correct": True})
    return block_id


class TestRoleGate:
    def test_a_learner_cannot_reach_the_trainer_surface(self, learner: Learner) -> None:
        for path in ("/trainer/cohort", "/trainer/agreement"):
            assert learner.get(path).status_code == 403

    def test_the_refusal_is_not_hostile(self, learner: Learner) -> None:
        message = learner.get("/trainer/cohort").json()["detail"]["message"]
        assert "for trainers" in message.lower()

    def test_an_anonymous_caller_is_refused_before_the_role_is_considered(
        self, anonymous
    ) -> None:
        assert anonymous.get("/trainer/cohort").status_code == 401


class TestCaseloadIsNotAccess:
    """The distinction the whole module is built around."""

    def test_linking_alone_reveals_nothing(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        practise(learner)
        trainer.post(
            "/trainer/link", json={"learner_user_id": learner.user_id, "display_name": "Ravi"}
        )

        cohort = trainer.get("/trainer/cohort").json()

        assert len(cohort) == 1
        assert cohort[0]["display_name"] == "Ravi"
        assert cohort[0]["shared"] is False
        # Named, because the trainer assigned them. No metrics, because the
        # learner has not agreed.
        assert cohort[0]["cards_started"] is None
        assert cohort[0]["lapses"] is None

    def test_linking_says_plainly_that_it_is_not_access(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        message = trainer.post(
            "/trainer/link", json={"learner_user_id": learner.user_id}
        ).json()["message"]

        assert "choose to share" in message.lower()

    def test_consent_alone_reveals_nothing_either(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        """A learner who shares is not thereby visible to every trainer alive."""
        share(learner)
        assert trainer.get("/trainer/cohort").json() == []

    def test_both_together_reveal_the_learner(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        practise(learner)
        share(learner)
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})

        member = trainer.get("/trainer/cohort").json()[0]

        assert member["shared"] is True
        assert member["cards_started"] == 1
        assert member["last_active_at"] is not None

    def test_withdrawing_consent_hides_the_data_again(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        """Consent a learner cannot withdraw is not consent."""
        practise(learner)
        share(learner)
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})
        assert trainer.get("/trainer/cohort").json()[0]["shared"] is True

        share(learner, granted=False)

        member = trainer.get("/trainer/cohort").json()[0]
        assert member["shared"] is False
        assert member["cards_started"] is None

    def test_a_trainer_sees_only_their_own_caseload(
        self, trainer: Trainer, learner: Learner, other_learner: Learner
    ) -> None:
        share(learner)
        share(other_learner)
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})

        cohort = trainer.get("/trainer/cohort").json()
        assert [m["learner_user_id"] for m in cohort] == [learner.user_id]

    def test_unlinking_removes_them(self, trainer: Trainer, learner: Learner) -> None:
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})
        trainer.delete(f"/trainer/link/{learner.user_id}")

        assert trainer.get("/trainer/cohort").json() == []


class TestLearnerDetail:
    def test_an_unlinked_learner_is_a_404(self, trainer: Trainer, learner: Learner) -> None:
        assert trainer.get(f"/trainer/learner/{learner.user_id}").status_code == 404

    def test_a_linked_but_unshared_learner_is_explained_not_refused(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        """200, not 403. The trainer legitimately has this person on their
        caseload; there is simply nothing to show. An error would read as a
        fault when it is a choice the learner made."""
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})

        response = trainer.get(f"/trainer/learner/{learner.user_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["shared"] is False
        assert "not chosen to share" in body["message"]
        assert "profile" not in body

    def test_a_shared_learner_shows_their_profile_and_summary(
        self, trainer: Trainer, learner: Learner
    ) -> None:
        learner.put(
            "/profile",
            json={
                "input_channels": ["aac"],
                "output_channels": ["easy_read", "pictograph"],
                "text_complexity": "easy_read",
                "speech_status": "nonverbal",
            },
        )
        practise(learner)
        share(learner)
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})

        body = trainer.get(f"/trainer/learner/{learner.user_id}").json()

        assert body["shared"] is True
        # The profile is shown so a trainer can tell a change in scores that
        # followed a change in settings from a change in ability.
        assert body["profile"]["text_complexity"] == "easy_read"
        assert body["summary"]["cards_started"] == 1


class TestEthicsE5:
    """Every AI score is overridable by a human, and every override is recorded.

    This is the test the Ethics Charter names. Until now E5 read
    NOT YET ENFORCED, because there was no trainer surface at all.
    """

    @pytest.fixture
    def scored(self, learner: Learner, trainer: Trainer) -> str:
        from app.routers import conversation

        class Stub:
            async def score(self, question, answer, role_context):
                return {
                    "scored": True,
                    "dimensions": [{"name": "content_relevance", "score": 2}],
                    "strengths": ["You answered the question."],
                    "improvements": ["Add an example."],
                    "audit": {
                        "rubric_version": "rubric-v1",
                        "scored_dimensions": ["content_relevance"],
                        "excluded_dimensions": ["speech_rate", "articulation_quality"],
                        "prompt_hash": "abc",
                        "model_id": "scripted",
                    },
                }

        conversation._client = Stub()  # type: ignore[assignment]

        share(learner)
        trainer.post("/trainer/link", json={"learner_user_id": learner.user_id})

        return learner.post(
            "/interview/score",
            json={"question": "Your strengths?", "answer": "I am careful."},
        ).json()["audit_id"]

    def test_a_trainer_can_override_an_ai_score(
        self, trainer: Trainer, scored: str
    ) -> None:
        response = trainer.post(
            "/trainer/override",
            json={
                "audit_id": scored,
                "override": "This answer was strong; the example was implicit.",
                "reason": "The rubric missed the example because it was not signposted.",
            },
        )

        assert response.status_code == 200
        assert response.json()["overridden"] is True

    def test_the_override_is_recorded_with_its_reason(
        self, trainer: Trainer, scored: str
    ) -> None:
        body = trainer.post(
            "/trainer/override",
            json={
                "audit_id": scored,
                "override": "Stronger than scored.",
                "reason": "Implicit example.",
            },
        ).json()

        assert body["override"] == "Stronger than scored."
        assert body["reason"] == "Implicit example."

    def test_the_original_ai_score_survives_the_override(
        self, trainer: Trainer, scored: str
    ) -> None:
        """"The AI said X, the trainer said Y, because Z" is the record that
        makes the AI answerable. Overwriting would destroy the evidence."""
        body = trainer.post(
            "/trainer/override",
            json={"audit_id": scored, "override": "Stronger.", "reason": "Implicit example."},
        ).json()

        assert body["original_rubric_version"] == "rubric-v1"
        assert body["original_scored_dimensions"] == ["content_relevance"]

    def test_a_reason_is_required(self, trainer: Trainer, scored: str) -> None:
        """A specialist forced to articulate a disagreement usually sharpens it,
        and the text is the training signal for improving the rubric."""
        response = trainer.post(
            "/trainer/override", json={"audit_id": scored, "override": "Stronger.", "reason": ""}
        )
        assert response.status_code == 422

    def test_a_trainer_cannot_override_a_score_they_may_not_see(
        self, trainer: Trainer, learner: Learner, other_learner: Learner
    ) -> None:
        from app.routers import conversation

        class Stub:
            async def score(self, question, answer, role_context):
                return {
                    "scored": True,
                    "dimensions": [],
                    "strengths": [],
                    "improvements": [],
                    "audit": {"rubric_version": "rubric-v1", "model_id": "scripted"},
                }

        conversation._client = Stub()  # type: ignore[assignment]

        # A score belonging to someone who is not on this trainer's caseload.
        audit_id = other_learner.post(
            "/interview/score", json={"question": "q", "answer": "a"}
        ).json()["audit_id"]

        response = trainer.post(
            "/trainer/override",
            json={"audit_id": audit_id, "override": "x", "reason": "should not work"},
        )

        # 404, not 403: "not yours" and "does not exist" must be
        # indistinguishable, or audit ids become probeable.
        assert response.status_code == 404

    def test_agreement_starts_at_one_and_falls_with_overrides(
        self, trainer: Trainer, scored: str
    ) -> None:
        """The most honest quality metric we have."""
        before = trainer.get("/trainer/agreement").json()
        assert before["scores"] == 1
        assert before["agreement"] == 1.0

        trainer.post(
            "/trainer/override",
            json={"audit_id": scored, "override": "Stronger.", "reason": "Implicit example."},
        )

        after = trainer.get("/trainer/agreement").json()
        assert after["overridden"] == 1
        assert after["agreement"] == 0.0

    def test_the_agreement_target_blames_the_scoring_not_the_trainers(
        self, trainer: Trainer
    ) -> None:
        body = trainer.get("/trainer/agreement").json()

        assert body["target_agreement"] == 0.85
        assert "not the trainers" in body["note"]

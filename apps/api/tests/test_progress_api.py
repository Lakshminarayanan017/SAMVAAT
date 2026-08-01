"""Progress, badges and recommendations, end to end.

The unit rules live in test_motivation.py. These check the API keeps them —
which is where a well-behaved module usually gets undone, by an endpoint that
helpfully adds a percentile.
"""

from __future__ import annotations

from tests.conftest import Learner


def practise(learner: Learner, count: int = 1) -> list[str]:
    items = learner.post(
        "/practice/session", json={"session_length_target_min": 20}
    ).json()["items"]

    done = []
    for item in items[:count]:
        learner.post("/practice/review", json={"block_id": item["block_id"], "correct": True})
        done.append(item["block_id"])
    return done


class TestProgress:
    def test_a_new_learner_starts_at_zero_and_is_welcomed(self, learner: Learner) -> None:
        body = learner.get("/progress").json()

        assert body["xp"] == 0
        assert body["days_practised"] == 0
        assert "welcome" in body["summary"].lower()

    def test_practising_earns_xp_and_records_the_day(self, learner: Learner) -> None:
        practise(learner, 3)
        body = learner.get("/progress").json()

        assert body["xp"] > 0
        assert body["days_practised"] == 1
        assert body["phrases_started"] == 3

    def test_a_phrase_is_not_reliable_after_one_correct_answer(
        self, learner: Learner
    ) -> None:
        """Answering right once is recall, not retention. Calling it mastery
        would tell a learner they know something they do not."""
        practise(learner, 1)
        assert learner.get("/progress").json()["phrases_reliable"] == 0

    def test_progress_never_mentions_other_learners(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        """ADR-0003 applied to motivation. A disabled learner has spent a
        lifetime being measured against a norm they were never going to meet."""
        practise(other_learner, 5)
        practise(learner, 1)

        body = learner.get("/progress").json()

        for field in body:
            for banned in ("percentile", "rank", "average", "cohort", "peers", "compared"):
                assert banned not in field
        assert "top " not in body["summary"].lower()

    def test_the_summary_never_scolds(self, learner: Learner) -> None:
        practise(learner, 1)
        summary = learner.get("/progress").json()["summary"].lower()

        for word in ("lost", "broken", "missed", "failed", "streak at risk"):
            assert word not in summary

    def test_progress_is_scoped_to_the_caller(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        practise(learner, 4)
        assert other_learner.get("/progress").json()["phrases_started"] == 0


class TestBadges:
    def test_a_first_practice_earns_a_badge(self, learner: Learner) -> None:
        practise(learner, 1)
        earned = {badge["id"] for badge in learner.get("/progress").json()["badges"]}
        assert "first_practice" in earned

    def test_the_whole_badge_set_is_visible_from_the_start(self, learner: Learner) -> None:
        """Hidden goals are a dark pattern; visible ones are a map."""
        badges = learner.get("/progress/badges").json()

        families = {badge["family"] for badge in badges}
        assert {"consistency", "mastery", "courage", "growth"} <= families

    def test_courage_badges_exist_and_name_what_they_are_for(
        self, learner: Learner
    ) -> None:
        badges = {b["id"]: b for b in learner.get("/progress/badges").json()}
        assert "disclosure_rehearsed" in badges
        assert "adjustment" in badges["disclosure_rehearsed"]["earned_message"].lower()


class TestRecommendations:
    def test_a_new_learner_is_given_somewhere_to_start(self, learner: Learner) -> None:
        picks = learner.get("/progress/next").json()

        assert picks
        assert all(pick["canonical_text"] for pick in picks)

    def test_every_recommendation_explains_itself(self, learner: Learner) -> None:
        """A recommendation the learner cannot interrogate is one they have to
        take on trust, and trust is what a disabled learner has least reason to
        extend to an algorithm."""
        for pick in learner.get("/progress/next").json():
            assert pick["explanation"]
            assert "{" not in pick["explanation"]
            assert pick["explanation"][0].isupper()
            assert pick["explanation"].endswith(".")

    def test_no_explanation_refers_to_anyone_else(self, learner: Learner) -> None:
        for pick in learner.get("/progress/next").json():
            lowered = pick["explanation"].lower()
            for word in ("others", "most people", "average", "than you", "everyone"):
                assert word not in lowered

    def test_the_limit_is_respected(self, learner: Learner) -> None:
        assert len(learner.get("/progress/next", params={"limit": 3}).json()) == 3

    def test_an_absurd_limit_is_rejected_rather_than_served(
        self, learner: Learner
    ) -> None:
        assert learner.get("/progress/next", params={"limit": 500}).status_code == 422

    def test_recommendations_are_scoped_to_the_caller(
        self, learner: Learner, other_learner: Learner
    ) -> None:
        practise(learner, 5)
        # The other learner has no history, so everything they see is new.
        picks = other_learner.get("/progress/next").json()
        assert picks


class TestAuth:
    def test_progress_requires_a_token(self, anonymous) -> None:
        for path in ("/progress", "/progress/next"):
            assert anonymous.get(path).status_code == 401

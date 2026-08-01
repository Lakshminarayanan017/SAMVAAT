"""Gamification and the recommender.

Motivation design is where accessibility gets betrayed most casually, because
the standard playbook is built on loss aversion. Most of these tests are about
what the system is not allowed to do.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime, timedelta, timezone

from app.learning.motivation import (
    BADGES,
    GRACE_DAYS,
    Attempt,
    BadgeFamily,
    LearnerProgress,
    PracticeRecord,
    award_xp,
    newly_earned,
)
from app.learning.recommend import (
    Candidate,
    LearnerContext,
    Reason,
    recommend,
    score_candidate,
)

TODAY = date(2026, 8, 1)
NOW = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


# ── XP ───────────────────────────────────────────────────────────────────────


class TestXpRewardsEffort:
    def test_xp_cannot_see_whether_the_answer_was_correct(self) -> None:
        """The strongest form the rule can take: there is no signature by which
        correctness could influence the number.

        Scoring correctness twice — once in FSRS, once in XP — would double the
        penalty for having a hard day.
        """
        assert "correct" not in inspect.signature(award_xp).parameters
        fields = Attempt.__dataclass_fields__
        for banned in ("correct", "score", "accuracy", "passed", "right"):
            assert not any(banned in name for name in fields), f"Attempt exposes '{banned}'"

    def test_every_attempt_earns_something(self) -> None:
        assert award_xp(Attempt()) > 0

    def test_harder_material_earns_more(self) -> None:
        """Attempting a level-5 self-advocacy phrase is worth more than a
        level-1 greeting, whether or not it goes well."""
        assert award_xp(Attempt(difficulty=5)) > award_xp(Attempt(difficulty=1))

    def test_new_material_earns_more_than_review(self) -> None:
        assert award_xp(Attempt(is_new=True)) > award_xp(Attempt(is_new=False))

    def test_returning_to_something_that_went_badly_earns_most(self) -> None:
        """That is the moment most learners quit, so it is the moment worth
        paying for."""
        assert award_xp(Attempt(had_lapsed=True)) > award_xp(Attempt(is_new=True))


# ── Practice days ────────────────────────────────────────────────────────────


class TestStreaksNeverPunish:
    def test_days_practised_only_ever_goes_up(self) -> None:
        record = PracticeRecord()
        for offset in (0, 1, 30, 31, 90):
            record = record.register(TODAY + timedelta(days=offset))

        assert record.days_practised == 5

    def test_a_long_absence_does_not_reduce_the_total(self) -> None:
        """The number a learner sees must never fall because they were ill."""
        record = PracticeRecord()
        for day in range(10):
            record = record.register(TODAY + timedelta(days=day))
        before = record.days_practised

        after = record.register(TODAY + timedelta(days=200))

        assert after.days_practised == before + 1
        assert after.current_run == 1  # quietly restarted

    def test_a_short_gap_keeps_the_run(self) -> None:
        """Fatigue, an appointment, a carer being unavailable — none of those
        should cost a learner their run."""
        record = PracticeRecord().register(TODAY)
        resumed = record.register(TODAY + timedelta(days=GRACE_DAYS + 1))

        assert resumed.current_run == 2

    def test_practising_twice_in_a_day_counts_once(self) -> None:
        """Nobody is nudged into grinding."""
        record = PracticeRecord().register(TODAY).register(TODAY)
        assert record.days_practised == 1

    def test_the_longest_run_is_remembered_even_after_a_break(self) -> None:
        record = PracticeRecord()
        for day in range(6):
            record = record.register(TODAY + timedelta(days=day))
        record = record.register(TODAY + timedelta(days=100))

        assert record.longest_run == 6
        assert record.current_run == 1

    def test_the_message_never_mentions_a_broken_streak(self) -> None:
        record = PracticeRecord()
        for day in range(5):
            record = record.register(TODAY + timedelta(days=day))
        after_a_break = record.register(TODAY + timedelta(days=90))

        message = after_a_break.summary().lower()

        for word in ("lost", "broken", "missed", "failed", "restart", "gone", "reset"):
            assert word not in message, f"summary mentions '{word}': {message!r}"

    def test_coming_back_is_welcomed_rather_than_scolded(self) -> None:
        record = PracticeRecord()
        for day in range(3):
            record = record.register(TODAY + timedelta(days=day))
        later = TODAY + timedelta(days=60)

        assert "good to see you again" in record.register(later).summary().lower()

    def test_a_first_session_is_welcomed(self) -> None:
        assert "welcome" in PracticeRecord().summary().lower()


# ── Badges ───────────────────────────────────────────────────────────────────


class TestBadges:
    def test_courage_and_growth_are_rewarded_not_only_accuracy(self) -> None:
        """Rehearsing a disclosure conversation is harder, and matters more,
        than getting ten greetings right."""
        families = {badge.family for badge in BADGES}
        assert BadgeFamily.COURAGE in families
        assert BadgeFamily.GROWTH in families

    def test_the_disclosure_badge_says_why_it_matters(self) -> None:
        badge = next(b for b in BADGES if b.id == "disclosure_rehearsed")
        assert "adjustment" in badge.earned_message.lower()

    def test_no_badge_compares_the_learner_to_anyone_else(self) -> None:
        """ADR-0003 applies to motivation as much as to scoring."""
        for badge in BADGES:
            text = f"{badge.label} {badge.earned_message}".lower()
            for word in ("rank", "top ", "percentile", "others", "beat", "than most",
                         "leaderboard", "average learner"):
                assert word not in text, f"{badge.id} compares: {text!r}"

    def test_no_badge_message_is_pitying(self) -> None:
        """Vague praise reads as pity, and disabled learners get enough of it."""
        for badge in BADGES:
            text = badge.earned_message.lower()
            for word in ("brave", "inspiring", "amazing", "special", "despite", "even though"):
                assert word not in text, f"{badge.id} is pitying: {text!r}"

    def test_badges_are_earned_from_this_learners_history_alone(self) -> None:
        fields = LearnerProgress.__dataclass_fields__
        for banned in ("cohort", "average", "percentile", "rank", "peers", "others"):
            assert not any(banned in name for name in fields)

    def test_a_badge_is_not_awarded_twice(self) -> None:
        progress = LearnerProgress(days_practised=7, earned={"first_practice"})
        earned = {badge.id for badge in newly_earned(progress)}

        assert "seven_days" in earned
        assert "first_practice" not in earned

    def test_coming_back_earns_a_badge(self) -> None:
        progress = LearnerProgress(days_practised=4, returned_after_break=True)
        assert "came_back" in {badge.id for badge in newly_earned(progress)}

    def test_a_personal_best_is_measured_against_the_learner(self) -> None:
        badge = next(b for b in BADGES if b.id == "own_best")
        assert "nobody else" in badge.earned_message.lower()


# ── Recommendations ──────────────────────────────────────────────────────────


def candidate(block_id: str, **kwargs) -> Candidate:
    return Candidate(block_id=block_id, **kwargs)


class TestRecommendations:
    def test_every_recommendation_carries_a_readable_reason(self) -> None:
        """Explainability is a product feature, not a debug tool. A trainer who
        cannot see why an item was chosen will override everything or nothing."""
        picks = recommend(
            [candidate("a", due_at=NOW - timedelta(days=5)), candidate("b", is_new=True)],
            LearnerContext(now=NOW),
        )

        for pick in picks:
            assert pick.explanation
            assert not pick.explanation.startswith("{")
            # Written for a learner, not lifted from the enum.
            assert pick.explanation[0].isupper()

    def test_a_weak_sound_outweighs_being_merely_due(self) -> None:
        """The one genuinely personal signal here."""
        picks = recommend(
            [
                candidate("due", due_at=NOW - timedelta(days=2)),
                candidate("weak", phonemes=("R", "L")),
            ],
            LearnerContext(weak_phonemes=("R",), now=NOW),
        )

        assert picks[0].block_id == "weak"
        assert picks[0].reason is Reason.WEAK_SOUND

    def test_a_phoneme_is_explained_in_words_a_learner_understands(self) -> None:
        """ARPAbet is unreadable. "the /r/ sound" is not."""
        _, reason, explanation = score_candidate(
            candidate("x", phonemes=("R",)), LearnerContext(weak_phonemes=("R",), now=NOW)
        )

        assert reason is Reason.WEAK_SOUND
        assert "/r/" in explanation
        assert "ARPAbet" not in explanation and "R" not in explanation.replace("/r/", "")

    def test_something_just_failed_is_pushed_down_not_forward(self) -> None:
        """Being handed the thing you just failed, twice, is how people decide
        an app is against them. Scheduling-suboptimal, and right anyway."""
        just_failed = candidate(
            "failed", due_at=NOW - timedelta(days=9), last_failed_at=NOW - timedelta(minutes=30)
        )
        ordinary = candidate("ordinary", due_at=NOW - timedelta(days=1))

        picks = recommend([just_failed, ordinary], LearnerContext(now=NOW))

        assert picks[0].block_id == "ordinary"

    def test_the_suppression_wears_off(self) -> None:
        """Suppressed, not removed. It comes back tomorrow."""
        stale_failure = candidate(
            "failed", due_at=NOW - timedelta(days=9), last_failed_at=NOW - timedelta(days=3)
        )
        picks = recommend(
            [stale_failure, candidate("ordinary", due_at=NOW - timedelta(days=1))],
            LearnerContext(now=NOW),
        )

        assert picks[0].block_id == "failed"

    def test_goal_relevant_material_is_favoured(self) -> None:
        picks = recommend(
            [
                candidate("generic", due_at=NOW - timedelta(days=1)),
                candidate("relevant", scenario_tags=("safety",), due_at=NOW - timedelta(days=1)),
            ],
            LearnerContext(goal_tags=("safety",), job_context="the warehouse", now=NOW),
        )

        assert picks[0].block_id == "relevant"
        assert "warehouse" in picks[0].explanation

    def test_low_self_reported_confidence_is_listened_to(self) -> None:
        _, reason, _ = score_candidate(
            candidate("unsure", last_self_report=1), LearnerContext(now=NOW)
        )
        assert reason is Reason.LOW_CONFIDENCE

    def test_the_list_opens_with_something_likely_to_go_well(self) -> None:
        """Confidence at the start of a session decides whether there is a next
        session."""
        picks = recommend(
            [
                candidate("hard", difficulty=5, due_at=NOW - timedelta(days=30)),
                candidate("easy", difficulty=1, due_at=NOW - timedelta(days=1)),
            ],
            LearnerContext(now=NOW),
        )

        assert picks[0].block_id == "easy"
        assert picks[0].reason is Reason.EASY_WIN

    def test_it_never_returns_more_than_asked_for(self) -> None:
        picks = recommend([candidate(f"p{i}") for i in range(20)], LearnerContext(now=NOW), limit=3)
        assert len(picks) == 3

    def test_an_empty_bank_returns_nothing_rather_than_failing(self) -> None:
        assert recommend([], LearnerContext(now=NOW)) == []

    def test_no_reason_refers_to_another_learner(self) -> None:
        from app.learning.recommend import REASON_TEXT

        for text in REASON_TEXT.values():
            lowered = text.lower()
            for word in ("others", "most people", "average", "than you", "peers", "everyone else"):
                assert word not in lowered, f"reason compares: {text!r}"

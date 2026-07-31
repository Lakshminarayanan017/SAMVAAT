"""Practice loop: FSRS scheduling, grade derivation, session assembly.

The scheduling tests check the algorithm behaves as FSRS specifies. The grading
and session tests check the *accessibility* decisions hold — those are the ones
that would silently regress and quietly disadvantage a learner.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.learning.fsrs import CardState, Fsrs, Grade
from app.learning.grading import Attempt, derive_grade, is_lapse
from app.learning.session import Candidate, build_session, item_budget

NOW = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def fsrs() -> Fsrs:
    return Fsrs()


# ── FSRS ──────────────────────────────────────────────────────────────────────


class TestFsrs:
    def test_rejects_a_wrong_number_of_weights(self) -> None:
        with pytest.raises(ValueError, match="17 weights"):
            Fsrs(weights=(0.1, 0.2))

    def test_first_review_stability_rises_with_the_grade(self, fsrs: Fsrs) -> None:
        stabilities = [fsrs.new_card(g, NOW).stability for g in Grade]
        assert stabilities == sorted(stabilities)

    def test_first_review_difficulty_falls_as_the_grade_rises(self, fsrs: Fsrs) -> None:
        difficulties = [fsrs.new_card(g, NOW).difficulty for g in Grade]
        assert difficulties == sorted(difficulties, reverse=True)

    def test_difficulty_stays_inside_bounds_under_sustained_failure(self, fsrs: Fsrs) -> None:
        card = fsrs.new_card(Grade.AGAIN, NOW)
        for day in range(40):
            card = fsrs.review(card, Grade.AGAIN, NOW + timedelta(days=day))
        assert 1.0 <= card.difficulty <= 10.0

    def test_repeated_success_lengthens_the_interval(self, fsrs: Fsrs) -> None:
        card = fsrs.new_card(Grade.GOOD, NOW)
        intervals = [card.due_at - NOW]

        for _ in range(6):
            reviewed_at = card.due_at
            card = fsrs.review(card, Grade.GOOD, reviewed_at)
            intervals.append(card.due_at - reviewed_at)

        # Each successful review schedules further out than the last.
        assert intervals == sorted(intervals)
        assert intervals[-1] > intervals[0]

    def test_a_lapse_shortens_the_interval_sharply(self, fsrs: Fsrs) -> None:
        card = fsrs.new_card(Grade.GOOD, NOW)
        for _ in range(4):
            card = fsrs.review(card, Grade.GOOD, card.due_at)

        before = card.due_at - card.last_reviewed_at  # type: ignore[operator]
        lapsed = fsrs.review(card, Grade.AGAIN, card.due_at)
        after = lapsed.due_at - lapsed.last_reviewed_at  # type: ignore[operator]

        assert after < before
        assert lapsed.lapses == card.lapses + 1

    def test_retrievability_decays_with_time_and_never_leaves_zero_to_one(self) -> None:
        card = CardState(stability=10.0, difficulty=5.0, due_at=NOW, last_reviewed_at=NOW)

        values = [card.retrievability(NOW + timedelta(days=d)) for d in (0, 1, 10, 100, 3650)]

        assert values == sorted(values, reverse=True)
        assert all(0.0 < v <= 1.0 for v in values)

    def test_interval_respects_the_maximum(self) -> None:
        scheduler = Fsrs(maximum_interval_days=30)
        card = scheduler.new_card(Grade.EASY, NOW)
        for _ in range(20):
            card = scheduler.review(card, Grade.EASY, card.due_at)

        assert (card.due_at - card.last_reviewed_at) <= timedelta(days=30)  # type: ignore[operator]

    def test_higher_desired_retention_schedules_sooner(self) -> None:
        relaxed = Fsrs(desired_retention=0.85).new_card(Grade.GOOD, NOW)
        strict = Fsrs(desired_retention=0.95).new_card(Grade.GOOD, NOW)
        assert strict.due_at < relaxed.due_at

    def test_a_same_instant_review_does_not_inflate_stability(self, fsrs: Fsrs) -> None:
        """Answering something you have not had time to forget proves nothing.

        FSRS encodes this: the growth term `exp(w10 * (1 - R)) - 1` goes to zero
        as retrievability approaches 1. It matters for us because a learner
        retrying an item inside one session is common — and must not be able to
        inflate an interval by simply answering the same phrase repeatedly.
        """
        card = fsrs.new_card(Grade.GOOD, NOW)
        repeated = fsrs.review(card, Grade.GOOD, NOW)

        assert repeated.stability == pytest.approx(card.stability, rel=1e-9)
        assert repeated.reps == 2

    def test_state_is_immutable(self, fsrs: Fsrs) -> None:
        card = fsrs.new_card(Grade.GOOD, NOW)
        reviewed = fsrs.review(card, Grade.GOOD, card.due_at)
        assert card.reps == 1 and reviewed.reps == 2

    def test_ninety_day_history_stays_numerically_sane(self, fsrs: Fsrs) -> None:
        """A long mixed history must not produce NaN, negative or runaway values."""
        card = fsrs.new_card(Grade.GOOD, NOW)
        pattern = [Grade.GOOD, Grade.GOOD, Grade.AGAIN, Grade.HARD, Grade.GOOD, Grade.EASY]

        for day in range(90):
            card = fsrs.review(card, pattern[day % len(pattern)], NOW + timedelta(days=day))
            assert card.stability > 0
            assert 1.0 <= card.difficulty <= 10.0
            assert card.due_at > NOW + timedelta(days=day)


# ── Grading ───────────────────────────────────────────────────────────────────


class TestGrading:
    def test_wrong_answer_is_again(self) -> None:
        assert derive_grade(Attempt(correct=False)) is Grade.AGAIN

    def test_clean_first_attempt_is_good(self) -> None:
        assert derive_grade(Attempt(correct=True)) is Grade.GOOD

    def test_second_attempt_is_hard(self) -> None:
        assert derive_grade(Attempt(correct=True, attempts=2)) is Grade.HARD

    def test_using_a_hint_is_hard(self) -> None:
        assert derive_grade(Attempt(correct=True, hints_used=1)) is Grade.HARD

    def test_high_confidence_promotes_a_clean_answer_to_easy(self) -> None:
        assert derive_grade(Attempt(correct=True, confidence=5)) is Grade.EASY

    def test_self_report_can_promote_but_never_demote(self) -> None:
        """A learner who under-rates themselves must not be punished for it."""
        assert derive_grade(Attempt(correct=True, confidence=1)) is Grade.GOOD

    def test_derive_grade_cannot_see_timing_at_all(self) -> None:
        """Ethics E6 and E2, enforced structurally rather than by discipline.

        `Attempt` has no duration field and `derive_grade` takes no timing
        argument, so response latency cannot influence scheduling. A learner who
        is slower *because of their disability* must never have material
        re-taught to them for it.
        """
        import inspect

        assert "duration" not in inspect.signature(derive_grade).parameters
        fields = Attempt.__dataclass_fields__
        for banned in ("duration", "latency", "elapsed", "seconds", "time", "speed"):
            assert not any(banned in name for name in fields), f"Attempt exposes '{banned}'"

    def test_unreliable_transcription_is_never_counted_against_the_learner(self) -> None:
        """An ASR weakness must not surface as the learner's weakness."""
        attempt = Attempt(correct=False, low_confidence_input=True)

        assert derive_grade(attempt) is not Grade.AGAIN
        assert is_lapse(attempt) is False

    def test_a_genuine_wrong_answer_is_a_lapse(self) -> None:
        assert is_lapse(Attempt(correct=False)) is True


# ── Session assembly ──────────────────────────────────────────────────────────


def card(
    *,
    due_days: float = -1,
    lapses: int = 0,
    difficulty: float = 5.0,
    reps: int = 3,
) -> CardState:
    return CardState(
        stability=10.0,
        difficulty=difficulty,
        due_at=NOW + timedelta(days=due_days),
        reps=reps,
        lapses=lapses,
        last_reviewed_at=NOW - timedelta(days=5),
    )


class TestItemBudget:
    def test_slower_input_modes_get_fewer_items_for_the_same_minutes(self) -> None:
        """The modality is slower, not the learner. Same five minutes either way."""
        assert item_budget(5, "switch") < item_budget(5, "aac") < item_budget(5, "text")

    def test_one_step_per_screen_reduces_the_count(self) -> None:
        assert item_budget(10, "text", one_step_per_screen=True) < item_budget(10, "text")

    def test_never_returns_a_trivially_short_session(self) -> None:
        assert item_budget(1, "switch", one_step_per_screen=True) >= 3


class TestBuildSession:
    def test_never_returns_an_empty_session_when_work_exists(self) -> None:
        candidates = [Candidate(f"p{i}", card(due_days=-i)) for i in range(10)]
        assert build_session(candidates, 5, "text", now=NOW).items

    def test_explains_itself_when_there_is_nothing_to_do(self) -> None:
        session = build_session([], 5, "text", now=NOW)
        assert session.items == []
        assert session.note

    def test_prefers_the_most_overdue_cards(self) -> None:
        candidates = [
            Candidate("recent", card(due_days=-1)),
            Candidate("ancient", card(due_days=-40)),
            Candidate("middling", card(due_days=-10)),
        ]
        items = build_session(candidates, 10, "text", now=NOW).items
        assert items.index("ancient") < items.index("recent")

    def test_caps_hard_items_to_protect_morale(self) -> None:
        hard = [Candidate(f"h{i}", card(due_days=-5, lapses=3, difficulty=9.0)) for i in range(8)]
        easy = [Candidate(f"e{i}", card(due_days=-5, difficulty=3.0)) for i in range(8)]

        items = build_session([*hard, *easy], 5, "text", now=NOW).items
        assert sum(1 for i in items if i.startswith("h")) <= 2

    def test_opens_with_an_item_the_learner_will_probably_get_right(self) -> None:
        candidates = [
            Candidate("hard", card(due_days=-30, lapses=4, difficulty=9.5)),
            Candidate("known", card(due_days=-2, difficulty=3.0, reps=8)),
        ]
        assert build_session(candidates, 5, "text", now=NOW).items[0] == "known"

    def test_falls_back_to_review_ahead_rather_than_a_short_session(self) -> None:
        """A learner who asked for eight minutes should get eight minutes."""
        candidates = [Candidate("due", card(due_days=-1))]
        candidates += [Candidate(f"future{i}", card(due_days=+i + 1)) for i in range(20)]

        session = build_session(candidates, 8, "text", now=NOW)
        assert len(session.items) == item_budget(8, "text")

    def test_new_material_is_introduced_easiest_first(self) -> None:
        candidates = [Candidate(f"n{d}", None, difficulty=d) for d in (5, 1, 3)]
        items = build_session(candidates, 10, "text", now=NOW).items
        assert items.index("n1") < items.index("n5")

    def test_estimate_reflects_the_input_mode(self) -> None:
        candidates = [Candidate(f"p{i}", card(due_days=-1)) for i in range(30)]

        text = build_session(candidates, 5, "text", now=NOW)
        switch = build_session(candidates, 5, "switch", now=NOW)

        # Both aim at the same five minutes; the switch user simply gets fewer,
        # not a rushed session.
        assert len(switch.items) < len(text.items)
        assert abs(text.estimated_seconds - switch.estimated_seconds) < 120

    def test_no_item_appears_twice(self) -> None:
        candidates = [Candidate(f"p{i}", card(due_days=-1)) for i in range(5)]
        items = build_session(candidates, 30, "text", now=NOW).items
        assert len(items) == len(set(items))

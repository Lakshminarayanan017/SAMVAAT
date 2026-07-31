"""FSRS — Free Spaced Repetition Scheduler (FSRS-4.5).

An implementation of the published algorithm, not an invention of ours. FSRS is
openly specified and empirically validated against very large review datasets;
SM-2 (the Anki default) is a 1980s heuristic that systematically over-schedules
easy material and under-schedules hard material.

Reference: https://github.com/open-spaced-repetition/fsrs4anki/wiki

The model tracks three quantities per card:

    stability      S   days until recall probability falls to 90%
    difficulty     D   1-10, how hard this item is *for this learner*
    retrievability R   0-1, probability of recall right now

Nothing in this module knows about disabilities, and that is deliberate: the
accessibility work lives in how a GRADE is derived (see grading.py), not in the
scheduling maths. Changing the maths per learner would make progress
incomparable and would quietly encode assumptions about who learns "slower".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import IntEnum

# ── Model constants ──────────────────────────────────────────────────────────

# The power forgetting curve introduced in FSRS-4.5.
DECAY = -0.5
FACTOR = 19 / 81

MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
MIN_STABILITY = 0.01

#: Published FSRS-4.5 default weights. Replaced by per-cohort optimised weights
#: once the pilot produces enough review history (M18).
DEFAULT_WEIGHTS: tuple[float, ...] = (
    0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.0310, 1.6474,
    0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.5870, 0.2272, 2.8755,
)


class Grade(IntEnum):
    """How well the learner did on a review.

    Derived from what the learner actually did (correctness, attempts, hints) —
    never from a self-rating and never from how long they took. See grading.py.
    """

    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True)
class CardState:
    """Scheduling state for one phrase, for one learner.

    Immutable: `review()` returns a new state. Review history is append-only, so
    a trainer can always reconstruct why a card is scheduled where it is.
    """

    stability: float
    difficulty: float
    due_at: datetime
    reps: int = 0
    lapses: int = 0
    last_reviewed_at: datetime | None = None

    def retrievability(self, now: datetime) -> float:
        """Probability of recall right now, from the power forgetting curve."""
        if self.last_reviewed_at is None:
            return 1.0
        elapsed = max(0.0, (now - self.last_reviewed_at).total_seconds() / 86_400)
        return (1 + FACTOR * elapsed / self.stability) ** DECAY

    def is_due(self, now: datetime) -> bool:
        return now >= self.due_at


class Fsrs:
    """The scheduler. Stateless — all state lives on the CardState."""

    def __init__(
        self,
        weights: tuple[float, ...] = DEFAULT_WEIGHTS,
        desired_retention: float = 0.9,
        maximum_interval_days: int = 365,
    ) -> None:
        if len(weights) != 17:
            raise ValueError(f"FSRS-4.5 expects 17 weights, got {len(weights)}")
        if not 0.7 <= desired_retention <= 0.98:
            raise ValueError("desired_retention outside a sensible range")

        self.w = weights
        self.desired_retention = desired_retention
        self.maximum_interval_days = maximum_interval_days

    # ── first review ─────────────────────────────────────────────────────────

    def new_card(self, grade: Grade, now: datetime | None = None) -> CardState:
        now = now or datetime.now(timezone.utc)

        stability = max(MIN_STABILITY, self.w[grade - 1])
        difficulty = self._initial_difficulty(grade)
        interval = self._interval(stability)

        return CardState(
            stability=stability,
            difficulty=difficulty,
            due_at=now + timedelta(days=interval),
            reps=1,
            lapses=1 if grade == Grade.AGAIN else 0,
            last_reviewed_at=now,
        )

    # ── subsequent reviews ───────────────────────────────────────────────────

    def review(self, card: CardState, grade: Grade, now: datetime | None = None) -> CardState:
        now = now or datetime.now(timezone.utc)
        retrievability = card.retrievability(now)

        difficulty = self._next_difficulty(card.difficulty, grade)

        if grade == Grade.AGAIN:
            stability = self._stability_after_lapse(card.stability, card.difficulty, retrievability)
        else:
            stability = self._stability_after_recall(
                card.stability, card.difficulty, retrievability, grade
            )

        stability = max(MIN_STABILITY, stability)

        return replace(
            card,
            stability=stability,
            difficulty=difficulty,
            due_at=now + timedelta(days=self._interval(stability)),
            reps=card.reps + 1,
            lapses=card.lapses + (1 if grade == Grade.AGAIN else 0),
            last_reviewed_at=now,
        )

    # ── internals ────────────────────────────────────────────────────────────

    def _interval(self, stability: float) -> float:
        """Days until retrievability decays to the desired retention."""
        interval = (stability / FACTOR) * (self.desired_retention ** (1 / DECAY) - 1)
        return min(max(interval, 1.0), float(self.maximum_interval_days))

    def _initial_difficulty(self, grade: Grade) -> float:
        return _clamp(self.w[4] - (grade - 3) * self.w[5], MIN_DIFFICULTY, MAX_DIFFICULTY)

    def _next_difficulty(self, difficulty: float, grade: Grade) -> float:
        delta = -self.w[6] * (grade - 3)
        # Linear damping: difficulty moves less the closer it already is to 10,
        # so one bad day cannot permanently mark an item as maximally hard.
        damped = difficulty + delta * (10 - difficulty) / 9
        # Mean reversion toward the difficulty of an "Easy" first review, which
        # stops difficulty from ratcheting upward over a long history.
        reverted = self.w[7] * self._initial_difficulty(Grade.EASY) + (1 - self.w[7]) * damped
        return _clamp(reverted, MIN_DIFFICULTY, MAX_DIFFICULTY)

    def _stability_after_recall(
        self, stability: float, difficulty: float, retrievability: float, grade: Grade
    ) -> float:
        hard_penalty = self.w[15] if grade == Grade.HARD else 1.0
        easy_bonus = self.w[16] if grade == Grade.EASY else 1.0

        growth = (
            math.exp(self.w[8])
            * (11 - difficulty)
            * stability ** -self.w[9]
            * (math.exp(self.w[10] * (1 - retrievability)) - 1)
            * hard_penalty
            * easy_bonus
        )
        return stability * (1 + growth)

    def _stability_after_lapse(
        self, stability: float, difficulty: float, retrievability: float
    ) -> float:
        return (
            self.w[11]
            * difficulty ** -self.w[12]
            * ((stability + 1) ** self.w[13] - 1)
            * math.exp(self.w[14] * (1 - retrievability))
        )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

"""The Personal Progress Index (M7, part C).

This is Idea 2, and it is the reason the product exists in the form it does.

    score != similarity(you, a non-disabled speaker)
    score  = f(you today, your own rolling baseline)

Every number a learner sees about their speech comes out of this module, and
every number that goes in is measured against that same learner's own history.
There is no reference speaker anywhere in this file, no target speech rate, no
"correct" pause length and no norm table. If one ever appears here, the product
has become the thing it was built to replace.

    PPI_d(t) = clamp( 50 + 15 * (x_d(t) - mu_d) / max(sigma_d, eps), 0, 100 )

50 is "exactly your own average". 65 is one standard deviation above your own
average. The learner competes with yesterday's self, and on a bad day the floor
is their own average rather than someone else's.

THE FOUR RULES THIS MODULE MUST OBEY
------------------------------------
R1. No output may reference a non-disabled reference speaker.
    Enforced by `tests/test_ppi.py::TestNoReferenceComparison`, which reads every
    learner-facing string this module can emit and fails on the vocabulary.

R2. A detected disfluency produces a coaching cue, never a deduction.
    The `fluency` dimension is baseline-relative like every other: a learner who
    stammers has a baseline that already contains their disfluency, so their
    index moves on change, not on presence. `attach_cues` carries the cues
    through untouched.

R3. The baseline is inspectable. Every DimensionScore carries the mean and the
    standard deviation it was computed against, and `explain()` states them in
    words. A trainer who cannot see why a number moved will not trust it, and a
    number a trainer does not trust does not get used.

R4. During calibration no numeric score is shown at all. Ten attempts is not
    enough history to say anything honest about a trend, and inventing one would
    teach the learner that the number is noise.

WHY PACE IS NOT SPEED
---------------------
`pace` measures rhythm steadiness, not words per minute. Scoring absolute speed
would reward speaking faster, which is a time-pressure mechanic wearing a
statistic's clothes (Ethics E6) — and speaking rate is a fixed characteristic of
dysarthria, not a skill anyone can practise their way out of. See ADR-0006.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

# ── Model constants ──────────────────────────────────────────────────────────

#: Attempts needed before a numeric score is honest (rule R4).
CALIBRATION_ATTEMPTS = 10

#: EWMA smoothing. Chosen so the baseline tracks over roughly three weeks of
#: daily practice rather than three days: alpha = 2/(N+1) with N = 21. A faster
#: baseline chases noise and tells a learner they are getting worse whenever
#: they have one good day followed by an ordinary one.
BASELINE_ALPHA = 0.09

#: Floor on the standard deviation used as the divisor. Without it, a learner
#: whose early attempts happen to be near-identical gets a near-zero sigma, and
#: the next ordinary attempt swings the index from 50 to 0 or 100.
MIN_SIGMA = 1e-3

#: Shrinkage prior on the spread. THIS IS NOT A DETAIL — it fixes a real defect
#: in the naive formula, and the defect is the exact harm the index exists to
#: avoid.
#:
#: The problem: a learner improving steadily has a small early variance, because
#: ten attempts on a rising line barely vary. Dividing by that small sigma gives
#: a large z and an index near 100 at attempt eleven. As their variance estimate
#: catches up with reality, the divisor grows and the index *falls* — from 80 to
#: 67 over forty sessions of genuine, uninterrupted improvement. The learner
#: works harder every day and watches the number go down.
#:
#: The fix is the standard shrinkage estimator: blend the learner's observed
#: variance with a prior, weighted by how much evidence there actually is. Early
#: on the prior dominates and scores are stable; later the learner's own spread
#: takes over and the score is genuinely theirs.
#:
#: PRIOR_SIGMA is a plausible spread on the 0-100 measurement scale. It is not a
#: claim about any population — it never enters as a mean, only as a
#: how-uncertain-are-we term, so it cannot make anyone's score a comparison.
PRIOR_SIGMA = 8.0
PRIOR_OBSERVATIONS = 12

#: How far one standard deviation moves the index.
SIGMA_POINTS = 15.0
CENTRE = 50.0


class Dimension(str, Enum):
    """The five things measured. Note what is absent.

    There is no dimension for accent, none for articulation quality against a
    standard, none for affect, and none for how long the learner took. Those are
    on the Ethics E2 exclusion list, and the way to keep them off a score is to
    have nowhere for them to go.
    """

    INTELLIGIBILITY = "intelligibility"
    PRONUNCIATION = "pronunciation"
    PACE = "pace"
    FLUENCY = "fluency"
    CONFIDENCE = "confidence"


#: Default composite weights, used when the profile carries none. Overridden per
#: learner from `CommunicationAbilityProfile.scoring_weights`, which is visible
#: to both learner and trainer and never hidden.
DEFAULT_WEIGHTS: dict[Dimension, float] = {
    Dimension.INTELLIGIBILITY: 0.30,
    Dimension.PRONUNCIATION: 0.20,
    Dimension.PACE: 0.15,
    Dimension.FLUENCY: 0.15,
    Dimension.CONFIDENCE: 0.20,
}

#: Plain-language names for the things being measured, in the learner's terms
#: rather than the pipeline's. Read by `explain()`.
DIMENSION_LABEL: dict[Dimension, str] = {
    Dimension.INTELLIGIBILITY: "how much of your message came through",
    Dimension.PRONUNCIATION: "how clearly the sounds came out",
    Dimension.PACE: "how evenly your speech flowed",
    Dimension.FLUENCY: "how smoothly the words came",
    Dimension.CONFIDENCE: "how sure you felt",
}


# ── Baselines ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Baseline:
    """One learner's rolling baseline for one dimension.

    Stored per learner per dimension rather than computed on read, so a trainer
    can inspect it, so it survives a change to the scoring code, and so the
    history that produced a score is auditable months later (rule R3).
    """

    dimension: Dimension
    mean: float = 0.0
    #: EWMA of the squared deviation. Kept as variance rather than as sigma so
    #: the update is a plain weighted average and cannot go negative.
    variance: float = 0.0
    #: Attempts observed. Drives the calibration gate, not the smoothing.
    observations: int = 0
    updated_at: datetime | None = None

    @property
    def sigma(self) -> float:
        """The learner's own observed spread. Reported, not used as the divisor."""
        return math.sqrt(max(0.0, self.variance))

    @property
    def effective_sigma(self) -> float:
        """The divisor the score actually uses: observed spread, shrunk toward
        the prior in proportion to how little evidence there is.

        See the PRIOR_SIGMA comment above for the defect this fixes.
        """
        weighted = (
            self.observations * max(0.0, self.variance)
            + PRIOR_OBSERVATIONS * PRIOR_SIGMA**2
        ) / (self.observations + PRIOR_OBSERVATIONS)

        return max(MIN_SIGMA, math.sqrt(weighted))

    @property
    def is_calibrated(self) -> bool:
        return self.observations >= CALIBRATION_ATTEMPTS

    def update(
        self,
        value: float,
        alpha: float = BASELINE_ALPHA,
        now: datetime | None = None,
    ) -> Baseline:
        """Fold one new observation in. Returns a new Baseline; never mutates.

        The first observation seeds the mean directly rather than pulling it 9%
        of the way from zero, which would otherwise make the learner's first ten
        scores a function of an arbitrary origin.
        """
        now = now or datetime.now(timezone.utc)

        if self.observations == 0:
            return replace(
                self,
                mean=value,
                variance=0.0,
                observations=1,
                updated_at=now,
            )

        # West's incremental EWMA variance: compute the deviation against the
        # OLD mean before moving it, otherwise the variance is systematically
        # under-estimated and every score is exaggerated.
        deviation = value - self.mean
        mean = self.mean + alpha * deviation
        variance = (1 - alpha) * (self.variance + alpha * deviation * deviation)

        return replace(
            self,
            mean=mean,
            variance=variance,
            observations=self.observations + 1,
            updated_at=now,
        )


class BaselineStore(Protocol):
    """The seam the Postgres `ppi_baselines` table fills in M17."""

    def get(self, user_id: str, dimension: Dimension) -> Baseline | None: ...

    def save(self, user_id: str, baseline: Baseline) -> None: ...

    def all_for_user(self, user_id: str) -> dict[Dimension, Baseline]: ...


class InMemoryBaselineStore:
    """Development-only baseline store."""

    def __init__(self) -> None:
        self._baselines: dict[tuple[str, Dimension], Baseline] = {}

    def get(self, user_id: str, dimension: Dimension) -> Baseline | None:
        return self._baselines.get((user_id, dimension))

    def save(self, user_id: str, baseline: Baseline) -> None:
        self._baselines[(user_id, baseline.dimension)] = baseline

    def all_for_user(self, user_id: str) -> dict[Dimension, Baseline]:
        return {
            dimension: baseline
            for (owner, dimension), baseline in self._baselines.items()
            if owner == user_id
        }

    def clear(self) -> None:
        self._baselines.clear()


# ── Scores ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DimensionScore:
    """One dimension of one attempt, with everything needed to explain it."""

    dimension: Dimension
    #: The measurement, in whatever unit the dimension uses. Internal.
    raw: float
    #: 0-100, or None during calibration. None means "we are not saying yet",
    #: which is a different and more honest statement than 50.
    score: int | None
    baseline_mean: float
    baseline_sigma: float
    observations: int

    @property
    def in_calibration(self) -> bool:
        return self.score is None

    def explain(self) -> str:
        """Rule R3, in words a learner reads.

        Deliberately states both numbers. "You improved" without the baseline is
        a claim; with the baseline it is evidence, and evidence is what makes a
        trainer trust the system enough to use it.
        """
        label = DIMENSION_LABEL[self.dimension]

        if self.in_calibration:
            remaining = max(0, CALIBRATION_ATTEMPTS - self.observations)
            return (
                f"We are still learning {label}. "
                f"About {remaining} more tries and we can show you the trend."
            )

        # A quarter of a standard deviation is the band inside which "you did
        # better" would be reading meaning into noise. Saying "the same as"
        # there is more useful, and more honest, than a direction.
        deviation = self.raw - self.baseline_mean
        if abs(deviation) < self.baseline_sigma * 0.25:
            direction = "the same as"
        else:
            direction = "above" if deviation > 0 else "below"

        return (
            f"Your usual for {label} is {self.baseline_mean:.0f}. "
            f"Today you were {self.raw:.0f} — {direction} your usual."
        )


@dataclass(frozen=True)
class CoachingCue:
    """Something to try. Never a record of something done wrong (rule R2)."""

    dimension: Dimension | None
    strategy: str
    message: str
    at_seconds: float | None = None


@dataclass(frozen=True)
class PpiResult:
    """Everything shown to a learner about one attempt."""

    dimensions: tuple[DimensionScore, ...]
    #: CAP-weighted composite, or None while any dimension is still calibrating.
    composite: int | None
    calibrating: bool
    #: The single line shown above the numbers. Written, not generated.
    message: str
    cues: tuple[CoachingCue, ...] = ()
    #: The weights used, echoed back so the learner and trainer can see them.
    #: They are never hidden — a weighting a learner cannot see is a judgement
    #: made about them behind their back.
    weights: tuple[tuple[str, float], ...] = ()

    def by_dimension(self, dimension: Dimension) -> DimensionScore | None:
        return next((d for d in self.dimensions if d.dimension is dimension), None)


def score_dimension(raw: float, baseline: Baseline) -> int | None:
    """The index for one dimension against one baseline.

    Returns None while the baseline is still calibrating (rule R4).
    """
    if not baseline.is_calibrated:
        return None

    z = (raw - baseline.mean) / baseline.effective_sigma
    return int(round(_clamp(CENTRE + SIGMA_POINTS * z, 0.0, 100.0)))


def compute(
    raw: dict[Dimension, float],
    baselines: dict[Dimension, Baseline],
    weights: dict[Dimension, float] | None = None,
    cues: tuple[CoachingCue, ...] = (),
) -> PpiResult:
    """Score one attempt against the learner's own history.

    Dimensions absent from `raw` are absent from the result rather than defaulted
    — a missing measurement is not a measurement of zero, and treating it as one
    would drag a composite down for a reason the learner cannot see or fix.
    """
    weights = weights or DEFAULT_WEIGHTS

    scores = tuple(
        DimensionScore(
            dimension=dimension,
            raw=value,
            score=score_dimension(value, baselines.get(dimension) or Baseline(dimension)),
            baseline_mean=(baselines.get(dimension) or Baseline(dimension)).mean,
            # The divisor the score used, not the raw observed spread. A trainer
            # asking "why did that move so little?" needs the number that
            # actually did the dividing.
            baseline_sigma=(baselines.get(dimension) or Baseline(dimension)).effective_sigma,
            observations=(baselines.get(dimension) or Baseline(dimension)).observations,
        )
        for dimension in Dimension
        if dimension in raw
        for value in [raw[dimension]]
    )

    calibrating = any(score.in_calibration for score in scores) or not scores
    composite = None if calibrating else _composite(scores, weights)

    return PpiResult(
        dimensions=scores,
        composite=composite,
        calibrating=calibrating,
        message=_message(composite, calibrating),
        cues=cues,
        weights=tuple(
            (dimension.value, weights.get(dimension, 0.0))
            for dimension in Dimension
            if dimension in raw
        ),
    )


def update_baselines(
    raw: dict[Dimension, float],
    baselines: dict[Dimension, Baseline],
    now: datetime | None = None,
) -> dict[Dimension, Baseline]:
    """Fold this attempt into the learner's baselines.

    Called AFTER `compute`, never before. Scoring an attempt against a baseline
    that already contains it pulls every score toward 50 and makes genuine
    improvement invisible — the learner would work harder and watch the number
    stay still.
    """
    updated = dict(baselines)

    for dimension, value in raw.items():
        current = updated.get(dimension) or Baseline(dimension)
        updated[dimension] = current.update(value, now=now)

    return updated


def _composite(scores: tuple[DimensionScore, ...], weights: dict[Dimension, float]) -> int:
    """Weighted mean over the dimensions that were actually measured.

    Weights are renormalised over what is present, so a learner whose attempt
    carried no self-report is not quietly scored as though their confidence
    were zero.
    """
    present = [(s, weights.get(s.dimension, 0.0)) for s in scores if s.score is not None]
    total_weight = sum(weight for _, weight in present)

    if total_weight <= 0:
        # Every weight was zero or absent. An unweighted mean is the honest
        # fallback; silently returning 50 would look like a real measurement.
        measured = [s.score for s in scores if s.score is not None]
        return int(round(sum(measured) / len(measured))) if measured else 50

    return int(round(sum(s.score * weight for s, weight in present) / total_weight))


def _message(composite: int | None, calibrating: bool) -> str:
    """The line above the numbers.

    Every branch here is checked by the no-reference-comparison test. Adding a
    cheerful comparison to "a typical speaker" would fail the build, which is
    the point.
    """
    if calibrating or composite is None:
        return "We are still learning how you speak. Keep going — this gets more useful every try."

    if composite >= 65:
        return "That was above your usual. Nicely done."
    if composite >= 45:
        return "That was right around your usual."
    return "That one was below your usual. Everyone has these — it does not undo your progress."


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

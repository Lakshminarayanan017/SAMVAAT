"""The Personal Progress Index.

This file contains the two tests that the entire ethical claim of the product
rests on, and they are gates rather than diagnostics:

  * `TestMonotonicity`     — a learner who improves sees their index rise.
  * `TestDisfluencyFairness` — a learner who stammers and a learner who does not,
                               improving identically, get indistinguishable
                               index trajectories.

If either fails, the build fails, and the correct response is to fix the scoring
rather than to relax the test. ADR-0003 is the argument; this is the proof.
"""

from __future__ import annotations

import random
import re

import pytest

from pipeline.ppi import (
    BASELINE_ALPHA,
    CALIBRATION_ATTEMPTS,
    DEFAULT_WEIGHTS,
    Baseline,
    CoachingCue,
    Dimension,
    InMemoryBaselineStore,
    compute,
    score_dimension,
    update_baselines,
)

#: Vocabulary that would mean the index had become a comparison to somebody
#: else. Checked against every string this module can put in front of a learner.
REFERENCE_WORDS = [
    "normal",
    "native",
    "typical",
    "standard speaker",
    "average speaker",
    "correct speaker",
    "fluent speaker",
    "non-disabled",
    "able-bodied",
    "compared to others",
    "other learners",
    "percentile",
    "rank",
]


def run_trajectory(
    values: list[float],
    dimension: Dimension = Dimension.FLUENCY,
) -> list[int | None]:
    """Score a sequence of attempts the way the runner does.

    Score first, then fold the attempt into the baseline. Reversing that order
    scores an attempt partly against itself, which drags every score toward 50
    and makes real improvement invisible — a learner would work harder and watch
    the number stand still.
    """
    baselines: dict[Dimension, Baseline] = {}
    trajectory: list[int | None] = []

    for value in values:
        raw = {dimension: value}
        trajectory.append(compute(raw, baselines).composite)
        baselines = update_baselines(raw, baselines)

    return trajectory


# ── Rule R4 — no number during calibration ───────────────────────────────────


class TestCalibration:
    def test_no_numeric_score_before_the_calibration_period_ends(self) -> None:
        """Ten attempts is not enough history to say anything honest about a
        trend. Inventing one teaches the learner the number is noise."""
        trajectory = run_trajectory([60.0] * (CALIBRATION_ATTEMPTS + 5))

        assert all(score is None for score in trajectory[:CALIBRATION_ATTEMPTS])
        assert all(score is not None for score in trajectory[CALIBRATION_ATTEMPTS:])

    def test_calibration_message_says_what_is_happening(self) -> None:
        result = compute({Dimension.FLUENCY: 60.0}, {})

        assert result.calibrating is True
        assert result.composite is None
        assert "still learning" in result.message.lower()

    def test_a_dimension_explains_its_own_calibration_state(self) -> None:
        result = compute({Dimension.PACE: 55.0}, {})
        explanation = result.dimensions[0].explain()

        assert "still learning" in explanation.lower()
        # Tells the learner roughly how much longer, so it reads as progress
        # rather than as the feature being broken.
        assert "more tries" in explanation.lower()


# ── The formula ──────────────────────────────────────────────────────────────


class TestScoreDimension:
    def _calibrated(
        self,
        mean: float,
        sigma: float,
        observations: int = CALIBRATION_ATTEMPTS,
    ) -> Baseline:
        return Baseline(
            dimension=Dimension.FLUENCY,
            mean=mean,
            variance=sigma**2,
            observations=observations,
        )

    def test_your_own_average_scores_fifty(self) -> None:
        """50 means 'exactly your usual'. That is the anchor the whole design
        hangs on: the midpoint is the learner, not a population."""
        assert score_dimension(70.0, self._calibrated(70.0, 5.0)) == 50

    def test_with_enough_history_one_sigma_above_scores_sixty_five(self) -> None:
        """The documented formula, once the shrinkage prior has washed out.

        `50 + 15z` is what the design promises; the prior only governs how fast
        the learner's own spread takes over from it.
        """
        settled = self._calibrated(70.0, 5.0, observations=800)
        assert score_dimension(75.0, settled) == 65
        assert score_dimension(65.0, settled) == 35

    def test_early_scores_are_pulled_toward_the_middle_on_purpose(self) -> None:
        """With ten attempts of evidence, a one-sigma day is not yet strong
        evidence of anything. Reporting it as a full 15-point move produces the
        falling-index-while-improving defect the prior exists to fix."""
        early = self._calibrated(70.0, 5.0, observations=CALIBRATION_ATTEMPTS)
        settled = self._calibrated(70.0, 5.0, observations=800)

        assert 50 < score_dimension(75.0, early) < score_dimension(75.0, settled)

    def test_more_evidence_moves_the_divisor_toward_the_learners_own_spread(self) -> None:
        spreads = [
            self._calibrated(70.0, 5.0, observations=n).effective_sigma
            for n in (10, 50, 200, 1000)
        ]
        assert spreads == sorted(spreads, reverse=True)
        assert spreads[-1] == pytest.approx(5.0, abs=0.1)

    def test_extreme_values_are_clamped_rather_than_overflowing(self) -> None:
        assert score_dimension(1000.0, self._calibrated(70.0, 5.0)) == 100
        assert score_dimension(-1000.0, self._calibrated(70.0, 5.0)) == 0

    def test_a_near_zero_sigma_does_not_produce_a_wild_swing(self) -> None:
        """A learner whose first attempts happen to be near-identical would
        otherwise get a sigma of ~0, and the next ordinary attempt would swing
        the index from 50 to 0 or 100 for no reason they could perceive."""
        identical = self._calibrated(70.0, 0.0)

        assert score_dimension(70.0, identical) == 50
        # Two points off their own average must not read as a catastrophe.
        assert 40 < score_dimension(68.0, identical) < 50

    def test_the_absolute_level_never_enters_the_score(self) -> None:
        """The heart of it: two learners at completely different absolute
        levels, each exactly at their own average, both score 50."""
        assert score_dimension(20.0, self._calibrated(20.0, 4.0)) == score_dimension(
            90.0, self._calibrated(90.0, 4.0)
        )


# ── The first fairness gate ──────────────────────────────────────────────────


class TestMonotonicity:
    def test_a_learner_who_improves_sees_their_index_rise(self) -> None:
        """The eval-harness target `ppi_monotonicity`.

        A learner improving steadily must see the number go up. If it does not,
        the index is not measuring what it claims to and no amount of kind copy
        around it will help.
        """
        improving = [50.0 + step * 0.8 for step in range(45)]
        scored = [s for s in run_trajectory(improving) if s is not None]

        third = len(scored) // 3
        assert sum(scored[-third:]) / third > sum(scored[:third]) / third

    def test_a_flat_learner_sits_at_their_own_average(self) -> None:
        """No change means no movement. An index that drifted on identical
        performance would be reporting the algorithm, not the learner."""
        scored = [s for s in run_trajectory([62.0] * 40) if s is not None]
        assert all(abs(score - 50) <= 2 for score in scored)

    def test_one_bad_day_does_not_erase_a_rising_trend(self) -> None:
        """Health fluctuates. A single dip must dent the index, not reset it —
        several of our learners have conditions where a bad week is expected and
        a scoring model that punishes it is a model they will stop opening."""
        values = [50.0 + step for step in range(30)]
        values[25] = 40.0

        scored = run_trajectory(values)
        assert scored[26] is not None and scored[24] is not None
        # The dip shows, and recovery is immediate rather than compounding.
        assert scored[25] is not None and scored[25] < scored[24]
        assert scored[26] > scored[25]


# ── The second fairness gate: the proof of ADR-0003 ──────────────────────────


class TestDisfluencyFairness:
    """Two speakers. Same content, same improvement, one stammers.

    This is the test the Ethics Charter points at, and it is the most important
    one in the repository. The mechanism it verifies is simple and worth stating
    plainly: because the baseline is the learner's own, a constant characteristic
    of their speech is absorbed into the baseline and cancels out of the score.
    Disability shifts the mean. It must not shift the index.
    """

    def test_a_constant_disfluency_offset_cancels_exactly(self) -> None:
        fluent = [55.0 + step * 0.5 for step in range(40)]
        # Identical trajectory, 25 points lower throughout — the acoustic
        # signature of a stammer that is present in every single attempt.
        stammering = [value - 25.0 for value in fluent]

        assert run_trajectory(fluent) == run_trajectory(stammering)

    def test_variable_disfluency_produces_indistinguishable_trajectories(self) -> None:
        """The realistic case: disfluency varies attempt to attempt.

        The two trajectories cannot be identical here, because the two speakers
        genuinely produced different signals. What must hold is that neither
        speaker is systematically scored lower — the difference must be noise
        around zero, not an offset.
        """
        rng = random.Random(20260731)

        improvement = [55.0 + step * 0.5 for step in range(60)]
        fluent = [value + rng.gauss(0, 3) for value in improvement]
        stammering = [value - 25.0 + rng.gauss(0, 3) for value in improvement]

        scored_fluent = [s for s in run_trajectory(fluent) if s is not None]
        scored_stammering = [s for s in run_trajectory(stammering) if s is not None]

        mean_fluent = sum(scored_fluent) / len(scored_fluent)
        mean_stammering = sum(scored_stammering) / len(scored_stammering)

        # Two points on a 0-100 scale, against a 25-point difference in the raw
        # signal. Any systematic penalty for stammering would be far larger.
        assert abs(mean_fluent - mean_stammering) < 2.0

    def test_the_stammering_speaker_is_not_pinned_to_the_floor(self) -> None:
        """The failure mode this replaces.

        A scorer measuring against a non-disabled reference gives P5 a low
        number forever, no matter what he does. Here his index must occupy the
        same range as anyone else's.
        """
        rng = random.Random(4)
        stammering = [30.0 + rng.gauss(0, 4) for _ in range(50)]

        scored = [s for s in run_trajectory(stammering) if s is not None]
        assert min(scored) < 50 < max(scored)
        assert 40 < sum(scored) / len(scored) < 60


# ── Rule R1 — no reference comparison anywhere ───────────────────────────────


class TestNoReferenceComparison:
    """Ethics E1, checked against every string the module can emit.

    A grep-style test rather than a review checklist, because a well-meaning
    copy change six months from now will not remember the rule and will not be
    reviewed by anyone who does.
    """

    def _assert_clean(self, text: str) -> None:
        # Word boundaries, not substrings: "renormalised" contains "normal" and
        # is a perfectly innocent statistics term. A test that cannot tell the
        # difference gets disabled by the first person it inconveniences, and
        # then it protects nothing.
        lowered = text.lower()
        for word in REFERENCE_WORDS:
            assert not re.search(rf"\b{re.escape(word)}\b", lowered), (
                f"reference comparison in copy: {text!r}"
            )

    def test_every_composite_message_is_clean(self) -> None:
        for composite in [None, 0, 25, 50, 60, 75, 100]:
            result = compute(
                {Dimension.FLUENCY: 50.0},
                {
                    Dimension.FLUENCY: Baseline(
                        Dimension.FLUENCY,
                        mean=float(composite or 50),
                        variance=25.0,
                        observations=CALIBRATION_ATTEMPTS,
                    )
                },
            )
            self._assert_clean(result.message)

    def test_every_dimension_explanation_is_clean(self) -> None:
        for dimension in Dimension:
            for observations in (0, 3, CALIBRATION_ATTEMPTS, 40):
                result = compute(
                    {dimension: 61.0},
                    {
                        dimension: Baseline(
                            dimension, mean=58.0, variance=9.0, observations=observations
                        )
                    },
                )
                self._assert_clean(result.dimensions[0].explain())

    def test_no_learner_facing_literal_in_the_module_compares_to_anyone(self) -> None:
        """Catches a comparison added in a code path no test happens to reach.

        Only short string literals are checked. The docstrings deliberately
        discuss what the module refuses to do — banning the vocabulary from the
        prose would make the file unable to explain itself.
        """
        import ast
        from pathlib import Path

        import pipeline.ppi as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)

        docstrings = {
            ast.get_docstring(node, clean=False)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
        }

        literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docstrings
        ]

        assert literals, "no string literals found — the parse went wrong"
        for literal in literals:
            self._assert_clean(literal)


# ── Rule R2 — cues, never deductions ─────────────────────────────────────────


class TestCoachingNeverDeducts:
    def test_cues_do_not_change_any_score(self) -> None:
        """Attaching coaching to a result must be inert. The moment a cue can
        move a number, a disfluency has become a penalty."""
        baselines = {
            Dimension.FLUENCY: Baseline(
                Dimension.FLUENCY, mean=60.0, variance=16.0, observations=30
            )
        }
        raw = {Dimension.FLUENCY: 64.0}

        without = compute(raw, baselines)
        with_cues = compute(
            raw,
            baselines,
            cues=(
                CoachingCue(Dimension.FLUENCY, "easy onset", "Try starting that word gently."),
                CoachingCue(Dimension.FLUENCY, "pausing", "A short pause works well here."),
            ),
        )

        assert without.composite == with_cues.composite
        assert [d.score for d in without.dimensions] == [d.score for d in with_cues.dimensions]

    def test_compute_has_no_parameter_that_could_carry_a_penalty(self) -> None:
        """Enforcement by signature: there is nowhere for a deduction to enter."""
        import inspect

        parameters = set(inspect.signature(compute).parameters)
        assert parameters == {"raw", "baselines", "weights", "cues"}


# ── Rule R3 — the baseline is inspectable ────────────────────────────────────


class TestBaselineIsInspectable:
    def test_a_score_carries_the_numbers_it_was_computed_from(self) -> None:
        baseline = Baseline(Dimension.PACE, mean=71.5, variance=36.0, observations=22)
        score = compute({Dimension.PACE: 78.0}, {Dimension.PACE: baseline}).dimensions[0]

        assert score.baseline_mean == pytest.approx(71.5)
        assert score.observations == 22
        # The divisor the score actually used, not the raw observed spread. A
        # trainer asking "why did that move so little?" needs the real number.
        assert score.baseline_sigma == pytest.approx(baseline.effective_sigma)

    def test_the_explanation_states_both_numbers(self) -> None:
        baselines = {
            Dimension.PACE: Baseline(Dimension.PACE, mean=92.0, variance=25.0, observations=30)
        }
        explanation = compute({Dimension.PACE: 104.0}, baselines).dimensions[0].explain()

        assert "92" in explanation
        assert "104" in explanation
        assert "above" in explanation

    def test_weights_are_returned_rather_than_hidden(self) -> None:
        """A weighting a learner cannot see is a judgement made about them
        behind their back."""
        result = compute(
            {Dimension.FLUENCY: 60.0, Dimension.INTELLIGIBILITY: 70.0},
            {},
            weights={Dimension.FLUENCY: 0.05, Dimension.INTELLIGIBILITY: 0.6},
        )

        assert dict(result.weights) == {"intelligibility": 0.6, "fluency": 0.05}


# ── Baseline mechanics ───────────────────────────────────────────────────────


class TestBaseline:
    def test_the_first_observation_seeds_the_mean_directly(self) -> None:
        """Otherwise the first ten scores are a function of an arbitrary origin
        rather than of the learner."""
        baseline = Baseline(Dimension.PACE).update(72.0)

        assert baseline.mean == pytest.approx(72.0)
        assert baseline.observations == 1

    def test_the_mean_tracks_a_sustained_change(self) -> None:
        baseline = Baseline(Dimension.PACE)
        for _ in range(60):
            baseline = baseline.update(80.0)

        assert baseline.mean == pytest.approx(80.0, abs=0.5)

    def test_the_baseline_tracks_over_weeks_not_days(self) -> None:
        """Tuned so one good day does not become the new standard the learner
        is then measured against and fails to meet."""
        baseline = Baseline(Dimension.PACE)
        for _ in range(20):
            baseline = baseline.update(50.0)

        after_one_spike = baseline.update(100.0)
        assert after_one_spike.mean < 56.0

    def test_alpha_is_the_documented_value(self) -> None:
        """A silent change here re-tunes every learner's baseline at once."""
        assert pytest.approx(2 / 22, abs=0.005) == BASELINE_ALPHA

    def test_updates_never_mutate(self) -> None:
        original = Baseline(Dimension.PACE, mean=50.0, variance=4.0, observations=5)
        original.update(90.0)
        assert original.mean == 50.0 and original.observations == 5

    def test_variance_is_never_negative(self) -> None:
        baseline = Baseline(Dimension.PACE)
        for value in [10.0, 90.0, 10.0, 90.0, 50.0]:
            baseline = baseline.update(value)
            assert baseline.variance >= 0
            assert baseline.sigma >= 0


class TestComposite:
    def test_missing_dimensions_cost_the_learner_nothing(self) -> None:
        """An attempt with no self-report must not be scored as though the
        learner's confidence were zero."""
        calibrated = {
            dimension: Baseline(dimension, mean=60.0, variance=25.0, observations=30)
            for dimension in Dimension
        }

        full = compute(dict.fromkeys(Dimension, 65.0), calibrated, DEFAULT_WEIGHTS)
        partial = compute(
            {Dimension.FLUENCY: 65.0, Dimension.PACE: 65.0}, calibrated, DEFAULT_WEIGHTS
        )

        assert full.composite == partial.composite

    def test_default_weights_sum_to_one(self) -> None:
        assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_all_five_dimensions_are_weighted(self) -> None:
        assert set(DEFAULT_WEIGHTS) == set(Dimension)


class TestBaselineStore:
    def test_round_trips_per_user_and_dimension(self) -> None:
        store = InMemoryBaselineStore()
        store.save("p3-arjun", Baseline(Dimension.PACE, mean=44.0, observations=12))
        store.save("p5-karthik", Baseline(Dimension.PACE, mean=71.0, observations=9))

        assert store.get("p3-arjun", Dimension.PACE).mean == 44.0
        assert store.get("p5-karthik", Dimension.PACE).mean == 71.0
        assert store.get("p3-arjun", Dimension.FLUENCY) is None

    def test_one_learners_baseline_never_leaks_into_anothers(self) -> None:
        store = InMemoryBaselineStore()
        store.save("p1-ravi", Baseline(Dimension.FLUENCY, mean=80.0, observations=20))

        assert store.all_for_user("p2-meena") == {}

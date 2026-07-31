"""The bias-guarded rubric (M11).

`TestDisfluencyInvariance` is the most important test in this repository. It is
the thing that converts a fairness claim into a fairness proof, and it is a gate
rather than a diagnostic: if it fails, the correct response is to fix the
scrubber, never to relax the tolerance.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from eval.invariance import (
    EPSILON,
    build_cases,
    inject_disfluencies,
    run_structural_gate,
)
from rubric.dimensions import (
    EXCLUDED_DIMENSIONS,
    MAX_SCORE,
    MIN_SCORE,
    ScoredDimension,
    is_excluded,
    scored_dimension_names,
    validate_response_shape,
)
from rubric.scorer import (
    RubricResult,
    TrainerOverride,
    apply_overrides,
)
from rubric.scrubber import scrub, strip_timing

# ── The gate ─────────────────────────────────────────────────────────────────


class TestDisfluencyInvariance:
    def test_every_fixture_scrubs_to_an_identical_string(self) -> None:
        """The strong claim, and it is free to check.

        If the two forms arrive at the scorer as the same string, the scorer
        cannot distinguish them — the fairness property holds by construction
        rather than by measurement.
        """
        for result in run_structural_gate():
            assert result.passed, f"{result.name}: {result.detail}"

    def test_epsilon_is_zero_not_merely_small(self) -> None:
        """A tolerance is a budget for scoring a learner lower for stammering,
        and there is no acceptable size for that budget."""
        assert EPSILON == 0

    def test_it_holds_across_many_random_injections(self) -> None:
        """One seed proves one case. Fairness is a property, not an anecdote."""
        for seed in range(60):
            for result in run_structural_gate(seed=seed):
                assert result.passed, f"seed {seed}, {result.name}: {result.detail}"

    def test_the_injector_actually_injects(self) -> None:
        """A gate that passes because nothing was changed proves nothing."""
        for case in build_cases():
            assert case.degraded != case.clean
            assert len(case.degraded) > len(case.clean)

    def test_injection_preserves_the_content_words(self) -> None:
        """The two transcripts must differ in disfluency and in nothing else,
        otherwise the gate is comparing two different answers."""
        for case in build_cases():
            assert case.scrubbed_clean == case.scrubbed_degraded


# ── The scrubber ─────────────────────────────────────────────────────────────


class TestScrubber:
    def test_removes_filled_pauses(self) -> None:
        assert "um" not in scrub("I worked, um, at the packaging unit").text.lower()

    def test_removes_sound_repetition(self) -> None:
        assert scrub("I w-w-worked there").text == "I worked there"

    def test_removes_word_repetition(self) -> None:
        assert scrub("I worked at the the packaging unit").text == "I worked at the packaging unit"

    def test_removes_repetition_across_a_sentence_boundary(self) -> None:
        """A learner who blocks after finishing a sentence and restarts the word
        produces this. A whitespace-only rule leaves it standing, and then the
        scorer sees two different texts."""
        assert scrub("I am very reliable. reliable.").text == "I am very reliable."

    def test_removes_pause_markers(self) -> None:
        assert "..." not in scrub("I worked ... at the unit").text

    def test_removes_transcriber_annotations(self) -> None:
        assert "[block]" not in scrub("I [block] worked there").text.lower()

    def test_keeps_a_self_correction(self) -> None:
        """A content revision, not a disfluency. The final claim is what should
        be scored, and removing the repair would change the meaning."""
        result = scrub("I worked at, sorry, I managed the packaging unit")
        assert "managed" in result.text

    def test_repairs_the_punctuation_it_damages(self) -> None:
        """A model scoring 'clarity' on mangled text marks it down, which would
        reintroduce the bias the scrubber exists to remove."""
        result = scrub("I worked, um, at the unit").text
        assert ", ," not in result
        assert " ." not in result
        assert result == "I worked, at the unit"

    def test_records_what_it_removed(self) -> None:
        result = scrub("I- I- I um worked ... there")
        assert result.changed
        assert result.removed_fillers >= 1
        assert result.removed_repetitions >= 1
        assert result.audit()["scrubbed"] is True

    def test_a_clean_transcript_survives_unchanged(self) -> None:
        clean = "I worked at the packaging unit for two years."
        assert scrub(clean).text == clean


class TestStripTiming:
    def test_removes_every_timing_field(self) -> None:
        """Models are extremely good at noticing a number that correlates with
        something, and terrible at being told not to."""
        payload = {
            "answer": "I worked there",
            "duration_seconds": 94,
            "latency_ms": 3100,
            "speech_rate_wpm": 61,
            "disfluency_events": [{"type": "block"}],
            "prosody": {"pause_ratio": 0.4},
        }

        result = strip_timing(payload)

        assert result == {"answer": "I worked there"}

    def test_strips_nested_timing(self) -> None:
        result = strip_timing({"attempt": {"answer": "x", "duration_seconds": 12}})
        assert result == {"attempt": {"answer": "x"}}

    def test_every_excluded_trait_has_a_field_that_is_stripped(self) -> None:
        """Guards the case where a new pipeline field ships and nobody adds it
        to the strip list."""
        payload = dict.fromkeys(
            ["speech_rate_wpm", "articulation_rate_wpm", "response_time", "gop", "audio_ref"], 1
        )
        assert strip_timing(payload) == {}


# ── The exclusion list ───────────────────────────────────────────────────────


class TestExclusionList:
    def test_the_charter_and_the_code_agree(self) -> None:
        """The charter is the human-readable original and this is the enforced
        copy. Editing one without the other must fail the build."""
        from pathlib import Path

        for parent in Path(__file__).resolve().parents:
            charter = parent / "docs" / "ETHICS_CHARTER.md"
            if charter.exists():
                break
        else:  # pragma: no cover
            pytest.fail("could not locate docs/ETHICS_CHARTER.md")

        text = charter.read_text(encoding="utf-8")

        for dimension in EXCLUDED_DIMENSIONS:
            assert dimension in text, (
                f"'{dimension}' is enforced in code but absent from the charter"
            )

        for dimension in scored_dimension_names():
            assert dimension in text, f"'{dimension}' is scored but absent from the charter"

    def test_there_are_exactly_six_scored_dimensions(self) -> None:
        assert len(scored_dimension_names()) == 6

    def test_no_scored_dimension_is_also_excluded(self) -> None:
        for name in scored_dimension_names():
            assert not is_excluded(name)

    def test_clarity_is_distinguished_from_articulation(self) -> None:
        """The dimension most at risk of quietly becoming an excluded one."""
        from rubric.dimensions import SPECS

        spec = SPECS[ScoredDimension.CLARITY_OF_INTENT]
        assert "NOT" in spec.not_this
        assert "articulated" in spec.not_this.lower()

    def test_self_advocacy_never_penalises_disclosure(self) -> None:
        from rubric.dimensions import SPECS

        spec = SPECS[ScoredDimension.SELF_ADVOCACY]
        assert "never penalise" in spec.not_this.lower()


class TestResponseValidation:
    def _valid(self) -> dict:
        return {"scores": dict.fromkeys(scored_dimension_names(), 3)}

    def test_accepts_a_well_formed_response(self) -> None:
        assert validate_response_shape(self._valid()) == []

    def test_rejects_an_excluded_dimension_as_an_ethics_breach(self) -> None:
        payload = self._valid()
        payload["scores"]["articulation_quality"] = 2

        problems = validate_response_shape(payload)
        assert any("Ethics E2" in problem for problem in problems)

    def test_rejects_an_unknown_dimension(self) -> None:
        payload = self._valid()
        payload["scores"]["charisma"] = 4
        assert any("unknown" in problem for problem in validate_response_shape(payload))

    def test_rejects_a_missing_dimension(self) -> None:
        payload = self._valid()
        del payload["scores"]["specificity"]
        assert any("specificity" in problem for problem in validate_response_shape(payload))

    def test_rejects_a_score_outside_the_scale(self) -> None:
        payload = self._valid()
        payload["scores"]["specificity"] = 9
        assert any("specificity" in problem for problem in validate_response_shape(payload))

    def test_rejects_a_missing_scores_object(self) -> None:
        assert validate_response_shape({}) != []


# ── Scoring behaviour ────────────────────────────────────────────────────────


class TestScorerWithoutAProvider:
    def test_refuses_to_invent_a_score(self, router) -> None:
        """The one scripted responder that will not do its job.

        An interview score is a judgement about someone's employability.
        Inventing one from authored text would put a fabricated assessment in
        front of a learner and into an audit record that claims to be reviewable.
        """
        from rubric.scorer import RubricScorer

        result = RubricScorer(router).score("Tell me about yourself", "I worked at a unit.")

        assert result.scored is False
        assert result.dimensions == ()
        assert "saved" in result.unavailable_message.lower()

    def test_the_interview_still_completes(self, router) -> None:
        """Scoring being unavailable must not lose the learner's work."""
        from rubric.scorer import RubricScorer

        result = RubricScorer(router).score("Q", "A")
        message = result.unavailable_message.lower()
        assert "trainer" in message or "back" in message

    def test_the_audit_record_exists_even_when_scoring_did_not(self, router) -> None:
        from rubric.scorer import RubricScorer

        audit = RubricScorer(router).score("Q", "A").audit

        assert audit["rubric_version"]
        assert audit["excluded_dimensions"] == list(EXCLUDED_DIMENSIONS)
        assert audit["input_scrubbing"]["scrubbed"] is True
        assert "scoring_unavailable" in audit["notes"]

    def test_the_audit_proves_what_was_not_graded(self, router) -> None:
        """Absence of evidence is not evidence of absence. An audit two years
        later has to be able to say what the rubric refused to grade."""
        from rubric.scorer import RubricScorer

        audit = RubricScorer(router).score("Q", "A").audit
        for dimension in EXCLUDED_DIMENSIONS:
            assert dimension in audit["excluded_dimensions"]


# ── Trainer override (Ethics E5) ─────────────────────────────────────────────


class TestTrainerOverride:
    def _result(self) -> RubricResult:
        from rubric.scorer import DimensionScore

        return RubricResult(
            scored=True,
            dimensions=tuple(
                DimensionScore(dimension=d, score=3, runs=(3, 3, 3)) for d in ScoredDimension
            ),
        )

    def _override(self, **kwargs) -> TrainerOverride:
        defaults = {
            "interview_run_id": "run-1",
            "dimension": ScoredDimension.SPECIFICITY,
            "original_score": 3,
            "new_score": 5,
            "trainer_user_id": "trainer-1",
            "reason": "The example was concrete; the model missed it.",
            "at": datetime.now(timezone.utc),
        }
        return TrainerOverride(**{**defaults, **kwargs})

    def test_an_override_changes_the_score(self) -> None:
        result = apply_overrides(self._result(), [self._override()])
        assert result.by_dimension(ScoredDimension.SPECIFICITY).score == 5

    def test_other_dimensions_are_untouched(self) -> None:
        result = apply_overrides(self._result(), [self._override()])
        assert result.by_dimension(ScoredDimension.CONTENT_RELEVANCE).score == 3

    def test_the_original_ai_score_survives(self) -> None:
        """'The trainer disagreed with the model here' is the signal the override
        rate measures, and destroying it would destroy the metric."""
        result = apply_overrides(self._result(), [self._override()])
        assert result.by_dimension(ScoredDimension.SPECIFICITY).runs == (3, 3, 3)

    def test_the_override_is_recorded_in_the_audit(self) -> None:
        result = apply_overrides(self._result(), [self._override()])
        recorded = result.audit["trainer_overrides"][0]

        assert recorded["from"] == 3
        assert recorded["to"] == 5
        assert recorded["trainer"] == "trainer-1"
        assert recorded["reason"]

    def test_an_override_without_a_reason_is_refused(self) -> None:
        """An unexplained override teaches the system nothing and gives the
        learner no way to understand the change."""
        with pytest.raises(ValueError, match="needs a reason"):
            self._override(reason="   ")

    def test_an_override_outside_the_scale_is_refused(self) -> None:
        with pytest.raises(ValueError, match=f"{MIN_SCORE}-{MAX_SCORE}"):
            self._override(new_score=9)


class TestInjector:
    def test_is_deterministic_for_a_seed(self) -> None:
        """A flaky fairness gate gets disabled, and a disabled fairness gate
        protects nobody."""
        text = "I worked at the packaging unit for two years."
        assert inject_disfluencies(text, seed=7) == inject_disfluencies(text, seed=7)

    def test_different_seeds_produce_different_disfluencies(self) -> None:
        text = "I worked at the packaging unit for two years and checked every box."
        assert inject_disfluencies(text, seed=1) != inject_disfluencies(text, seed=2)

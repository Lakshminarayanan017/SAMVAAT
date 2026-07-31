"""The bridge from pipeline output to the five raw measurements.

The properties worth guarding here are mostly about what a measure must NOT do:
must not reward speed, must not double-count an overlapping detection, must not
turn a missing measurement into a zero, and must not let a coaching cue become
a third improvement point.
"""

from __future__ import annotations

import pytest

from pipeline.measures import (
    MeasurementInput,
    attach_cues,
    confidence,
    intelligibility,
    raw_dimensions,
    rhythm_steadiness,
    smoothness,
)
from pipeline.ppi import CoachingCue, Dimension
from pipeline.prosody import ProsodyFeatures
from pipeline.types import PronunciationScore, Transcript


def prosody_with(runs: tuple[float, ...], duration: float = 6.0) -> ProsodyFeatures:
    return ProsodyFeatures(
        duration_seconds=duration,
        speech_rate_wpm=None,
        articulation_rate_wpm=None,
        pause_count=max(0, len(runs) - 1),
        total_pause_seconds=0.0,
        mean_pause_seconds=None,
        longest_pause_seconds=0.0,
        pause_ratio=0.0,
        speaking_runs_seconds=runs,
        voiced_ratio=0.8,
        f0_mean_hz=140.0,
        f0_range_hz=60.0,
        f0_std_hz=15.0,
        energy_mean=0.2,
        energy_std=0.05,
        energy_variation=0.25,
    )


class TestIntelligibility:
    def test_an_exact_match_is_full_marks(self) -> None:
        heard = "could you please repeat that"
        assert intelligibility(heard, "Could you please repeat that?") == 100.0

    def test_a_missing_word_costs_proportionally(self) -> None:
        score = intelligibility("could you repeat that", "could you please repeat that")
        assert score == pytest.approx(80.0)

    def test_nothing_heard_scores_zero(self) -> None:
        assert intelligibility("", "could you please repeat that") == 0.0

    def test_never_goes_negative_however_wrong_the_transcript(self) -> None:
        """A wildly wrong recognition is 0, not -400. A negative measurement
        would wreck the learner's baseline for every later attempt."""
        assert intelligibility("a b c d e f g h i j k l", "hello") >= 0.0

    def test_punctuation_and_case_do_not_change_the_answer(self) -> None:
        assert intelligibility("HELLO, THERE!", "hello there") == 100.0

    def test_it_measures_words_not_characters(self) -> None:
        """A learner who said 'finished' for 'completed' communicated. A
        character metric would rate that closer than 'I've finished' against
        'I finished', which is the opposite of the truth."""
        one_word_wrong = intelligibility("i have finished the batch", "i have completed the batch")
        assert one_word_wrong == pytest.approx(80.0)


class TestRhythmSteadiness:
    def test_even_chunks_score_higher_than_uneven_ones(self) -> None:
        even = rhythm_steadiness(prosody_with((1.0, 1.0, 1.0, 1.0)))
        uneven = rhythm_steadiness(prosody_with((0.2, 2.5, 0.3, 1.9)))

        assert even is not None and uneven is not None
        assert even > uneven

    def test_speed_does_not_enter_the_measure(self) -> None:
        """ADR-0006. Two learners with identical evenness, one speaking four
        times as slowly, must measure identically — otherwise the index rewards
        hurrying, which is a time-pressure mechanic (Ethics E6), and penalises
        dysarthria, which is not a skill gap."""
        fast = rhythm_steadiness(prosody_with((0.5, 0.5, 0.5), duration=2.0))
        slow = rhythm_steadiness(prosody_with((2.0, 2.0, 2.0), duration=8.0))

        assert fast == pytest.approx(slow)

    def test_a_single_unbroken_run_has_no_rhythm_to_measure(self) -> None:
        """Returning a perfect score would reward 'did not pause', which is
        exactly the thing several of our learners physically cannot do."""
        assert rhythm_steadiness(prosody_with((3.0,))) is None
        assert rhythm_steadiness(prosody_with(())) is None

    def test_the_result_is_bounded(self) -> None:
        for runs in [(1.0, 1.0), (0.05, 5.0), (1.0, 1.0, 1.0, 9.0)]:
            value = rhythm_steadiness(prosody_with(runs))
            assert value is not None and 0.0 < value <= 100.0


class TestSmoothness:
    def test_no_events_means_the_whole_utterance_is_smooth(self) -> None:
        assert smoothness((), duration_seconds=5.0) == 100.0

    def test_overlapping_detections_are_merged_before_counting(self) -> None:
        """The detector scans with 50% overlap, so one event is routinely
        reported by two windows. Summing the raw spans would double-count it
        into a far worse number than the speech deserves."""
        overlapping = smoothness(
            (("block", 0.0, 3.0), ("block", 1.5, 4.5)), duration_seconds=10.0
        )
        assert overlapping == pytest.approx(55.0, abs=0.1)

    def test_coverage_never_pushes_the_measure_below_zero(self) -> None:
        assert smoothness((("block", 0.0, 30.0),), duration_seconds=5.0) == 0.0

    def test_a_zero_length_utterance_does_not_divide_by_zero(self) -> None:
        assert smoothness((("block", 0.0, 1.0),), duration_seconds=0.0) == 100.0


class TestConfidence:
    def test_the_scale_maps_onto_the_shared_range(self) -> None:
        assert confidence(1) == 0.0
        assert confidence(3) == 50.0
        assert confidence(5) == 100.0

    def test_out_of_range_input_is_clamped_rather_than_extrapolated(self) -> None:
        assert confidence(0) == 0.0
        assert confidence(99) == 100.0


class TestRawDimensions:
    def test_an_unmeasurable_dimension_is_absent_rather_than_zero(self) -> None:
        """A missing measurement is not a measurement of zero. Defaulting would
        drag the composite down for a reason the learner can neither see nor fix."""
        raw = raw_dimensions(MeasurementInput(target_text="hello there"))
        assert raw == {}

    def test_unreliable_pronunciation_is_omitted(self) -> None:
        """GOP over a bad alignment is a confident number about nothing."""
        unreliable = PronunciationScore(phones=[], phrase_gop=-2.0, reliable=False)
        raw = raw_dimensions(
            MeasurementInput(target_text="hello", pronunciation=unreliable)
        )
        assert Dimension.PRONUNCIATION not in raw

    def test_a_full_attempt_produces_every_dimension(self) -> None:
        raw = raw_dimensions(
            MeasurementInput(
                target_text="could you please repeat that",
                transcript=Transcript(
                    text="could you please repeat that", confidence=0.9, model="test"
                ),
                pronunciation=PronunciationScore(phones=[], phrase_gop=-0.5, reliable=True),
                prosody=prosody_with((1.0, 1.2, 0.9)),
                disfluency_spans=(("block", 1.0, 2.0),),
                self_report_confidence=4,
            )
        )

        assert set(raw) == set(Dimension)
        for value in raw.values():
            assert 0.0 <= value <= 100.0

    def test_fluency_needs_prosody_for_its_denominator(self) -> None:
        """Without a duration there is nothing to express coverage against, so
        the dimension is omitted rather than invented."""
        raw = raw_dimensions(
            MeasurementInput(target_text="hello", disfluency_spans=(("block", 0.0, 1.0),))
        )
        assert Dimension.FLUENCY not in raw


class TestAttachCues:
    def test_never_more_than_two_improvement_points(self) -> None:
        """The Ethics Charter cap. More is not more helpful — it is
        demoralising, and for a learner with an intellectual disability it is
        unusable. Applied here once rather than trusted to every caller."""
        many = tuple(
            CoachingCue(Dimension.FLUENCY, "easy onset", f"Try this {n}.") for n in range(6)
        )
        assert len(attach_cues(many, None)) == 2

    def test_disfluency_cues_come_before_phoneme_suggestions(self) -> None:
        """They arrive already phrased as strategies from the SLP library."""
        pronunciation = PronunciationScore(
            phones=[], phrase_gop=-2.0, problem_phones=["R", "TH"], reliable=True
        )
        cues = attach_cues(
            (CoachingCue(Dimension.FLUENCY, "pausing", "Try a short pause."),),
            pronunciation,
        )

        assert cues[0].strategy == "pausing"
        assert cues[1].dimension is Dimension.PRONUNCIATION

    def test_unreliable_pronunciation_contributes_no_cue(self) -> None:
        cues = attach_cues(
            (),
            PronunciationScore(phones=[], phrase_gop=-2.0, problem_phones=["R"], reliable=False),
        )
        assert cues == ()

    def test_every_cue_is_phrased_as_something_to_try(self) -> None:
        cues = attach_cues(
            (),
            PronunciationScore(phones=[], phrase_gop=-2.0, problem_phones=["R"], reliable=True),
        )

        for cue in cues:
            lowered = cue.message.lower()
            assert "try" in lowered
            for blaming in ("wrong", "error", "mistake", "failed", "incorrect", "bad"):
                assert blaming not in lowered

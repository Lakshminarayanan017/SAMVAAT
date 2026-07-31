"""Goodness of Pronunciation.

The scoring maths is pure, so it is tested directly rather than inferred from
end-to-end behaviour. These tests pin the properties the Personal Progress Index
depends on — if GOP stops behaving as specified, every pronunciation score in
the product becomes meaningless and nothing else would notice.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.gop import (
    MAX_PROBLEM_PHONES,
    MIN_ALIGNMENT_SCORE,
    PROBLEM_GOP_THRESHOLD,
    aggregate_gop,
    frames_for,
    gop_to_percent,
    phone_gop,
    score_alignment,
    to_log_posteriors,
    worst_phones,
)
from pipeline.types import AlignedPhone, Alignment, Phone, PhoneScore

PHONES = ["k", "uh", "d", "j", "uu", "p", "l", "ii", "z"]
PHONE_INDEX = {symbol: index for index, symbol in enumerate(PHONES)}


def posteriors(frames: int, confident_phone: int | None = None, confidence: float = 20.0):
    """Log-posteriors where one phone optionally dominates every frame."""
    logits = np.zeros((frames, len(PHONES)), dtype=np.float64)
    if confident_phone is not None:
        logits[:, confident_phone] = confidence
    return to_log_posteriors(logits)


def aligned(symbol: str, start: float, end: float, word: int = 0) -> AlignedPhone:
    return AlignedPhone(
        phone=Phone(symbol=symbol, word_index=word, position_in_word=0),
        start_seconds=start,
        end_seconds=end,
    )


# ── log-softmax ───────────────────────────────────────────────────────────────


class TestLogPosteriors:
    def test_rows_sum_to_one_in_probability_space(self) -> None:
        result = np.exp(to_log_posteriors(np.random.randn(10, len(PHONES))))
        assert np.allclose(result.sum(axis=1), 1.0)

    def test_is_numerically_stable_on_extreme_logits(self) -> None:
        """The naive softmax overflows here and yields NaN, which would then
        propagate silently into every score downstream."""
        extreme = np.full((3, len(PHONES)), 1e4)
        extreme[:, 0] = 1e5

        result = to_log_posteriors(extreme)

        assert np.isfinite(result).all()
        assert not np.isnan(result).any()

    def test_all_values_are_non_positive(self) -> None:
        result = to_log_posteriors(np.random.randn(20, len(PHONES)) * 5)
        assert (result <= 1e-9).all()


# ── phone-level GOP ───────────────────────────────────────────────────────────


class TestPhoneGop:
    def test_is_zero_when_the_expected_phone_is_the_best_guess(self) -> None:
        log_post = posteriors(10, confident_phone=PHONE_INDEX["k"])
        assert phone_gop(log_post, 0, 10, PHONE_INDEX["k"]) == pytest.approx(0.0, abs=1e-9)

    def test_is_negative_when_the_model_heard_something_else(self) -> None:
        log_post = posteriors(10, confident_phone=PHONE_INDEX["p"])
        assert phone_gop(log_post, 0, 10, PHONE_INDEX["k"]) < -1.0

    def test_never_exceeds_zero(self) -> None:
        for _ in range(50):
            log_post = to_log_posteriors(np.random.randn(8, len(PHONES)) * 3)
            for index in range(len(PHONES)):
                assert phone_gop(log_post, 0, 8, index) <= 0.0

    def test_is_length_normalised(self) -> None:
        """A long phone must not score worse purely for occupying more frames.

        Without normalisation vowels would always look worse than stops, and the
        coaching target would be an artefact of phone duration rather than of
        anything the learner did.
        """
        log_post = posteriors(100, confident_phone=PHONE_INDEX["p"])

        short = phone_gop(log_post, 0, 5, PHONE_INDEX["k"])
        long = phone_gop(log_post, 0, 80, PHONE_INDEX["k"])

        assert short == pytest.approx(long, abs=1e-9)

    def test_an_empty_window_scores_zero_rather_than_crashing(self) -> None:
        assert phone_gop(posteriors(10), 5, 5, 0) == 0.0

    def test_confidence_of_the_wrong_phone_deepens_the_penalty(self) -> None:
        mild = posteriors(10, confident_phone=PHONE_INDEX["p"], confidence=2.0)
        strong = posteriors(10, confident_phone=PHONE_INDEX["p"], confidence=20.0)

        assert phone_gop(strong, 0, 10, PHONE_INDEX["k"]) < phone_gop(mild, 0, 10, PHONE_INDEX["k"])


# ── frame mapping ─────────────────────────────────────────────────────────────


class TestFramesFor:
    def test_maps_seconds_onto_frame_indices(self) -> None:
        start, end = frames_for(aligned("k", 0.10, 0.20), 0.02, 100)
        assert (start, end) == (5, 10)

    def test_clamps_to_the_posterior_matrix(self) -> None:
        start, end = frames_for(aligned("k", 0.0, 100.0), 0.02, 50)
        assert start >= 0 and end <= 50

    def test_always_yields_at_least_one_frame(self) -> None:
        """A zero-width window would make GOP silently zero, which reads as a
        perfect pronunciation."""
        start, end = frames_for(aligned("k", 0.1, 0.1), 0.02, 100)
        assert end > start


# ── aggregation ───────────────────────────────────────────────────────────────


class TestAggregate:
    def test_weights_by_duration(self) -> None:
        """A single mis-hit consonant must not dominate a sentence otherwise
        said well — a phrase is mostly vowels by time."""
        scores = [
            PhoneScore("uu", gop=0.0, duration_seconds=1.0, word_index=0),
            PhoneScore("k", gop=-10.0, duration_seconds=0.01, word_index=0),
        ]

        weighted = aggregate_gop(scores)
        flat = float(np.mean([s.gop for s in scores]))

        assert weighted > flat
        assert weighted > -0.2

    def test_is_zero_for_no_phones(self) -> None:
        assert aggregate_gop([]) == 0.0

    def test_falls_back_to_a_flat_mean_on_zero_durations(self) -> None:
        scores = [
            PhoneScore("k", gop=-2.0, duration_seconds=0.0, word_index=0),
            PhoneScore("p", gop=-4.0, duration_seconds=0.0, word_index=0),
        ]
        assert aggregate_gop(scores) == pytest.approx(-3.0)


# ── coaching targets ──────────────────────────────────────────────────────────


class TestWorstPhones:
    def test_returns_the_worst_first(self) -> None:
        scores = [
            PhoneScore("k", gop=-2.0, duration_seconds=0.1, word_index=0),
            PhoneScore("p", gop=-8.0, duration_seconds=0.1, word_index=0),
            PhoneScore("d", gop=-5.0, duration_seconds=0.1, word_index=0),
        ]
        assert worst_phones(scores) == ["p", "d", "k"]

    def test_is_capped(self) -> None:
        """More than three improvement points is demoralising and unusable —
        the same rule the interview rubric follows."""
        scores = [
            PhoneScore(symbol, gop=-5.0, duration_seconds=0.1, word_index=0)
            for symbol in PHONES
        ]
        assert len(worst_phones(scores)) == MAX_PROBLEM_PHONES

    def test_returns_nothing_when_everything_was_said_well(self) -> None:
        """Without a threshold every learner gets three 'problems' after a
        flawless attempt, which teaches them the number means nothing."""
        scores = [
            PhoneScore("k", gop=-0.1, duration_seconds=0.1, word_index=0),
            PhoneScore("p", gop=0.0, duration_seconds=0.1, word_index=0),
        ]
        assert worst_phones(scores) == []

    def test_respects_the_threshold_boundary(self) -> None:
        def scored(symbol: str, gop: float) -> PhoneScore:
            return PhoneScore(symbol, gop=gop, duration_seconds=0.1, word_index=0)

        just_above = scored("k", PROBLEM_GOP_THRESHOLD + 0.01)
        just_below = scored("p", PROBLEM_GOP_THRESHOLD - 0.01)

        assert worst_phones([just_above, just_below]) == ["p"]

    def test_does_not_repeat_a_symbol(self) -> None:
        scores = [
            PhoneScore("k", gop=-9.0, duration_seconds=0.1, word_index=0),
            PhoneScore("k", gop=-8.0, duration_seconds=0.1, word_index=1),
            PhoneScore("p", gop=-7.0, duration_seconds=0.1, word_index=1),
        ]
        assert worst_phones(scores) == ["k", "p"]


# ── whole-alignment scoring ───────────────────────────────────────────────────


class TestScoreAlignment:
    def test_scores_every_known_phone(self) -> None:
        log_post = posteriors(50, confident_phone=PHONE_INDEX["k"])
        alignment = Alignment(
            phones=[aligned("k", 0.0, 0.2), aligned("uh", 0.2, 0.4)],
            aligner="test",
        )

        result = score_alignment(log_post, alignment, PHONE_INDEX)

        assert [phone.symbol for phone in result.phones] == ["k", "uh"]
        assert result.phones[0].gop == pytest.approx(0.0, abs=1e-9)
        assert result.phones[1].gop < 0

    def test_skips_phones_the_model_cannot_output(self) -> None:
        """Scored as absent, never as zero — zero would read as perfect."""
        log_post = posteriors(50)
        alignment = Alignment(phones=[aligned("zzz", 0.0, 0.2)], aligner="test")

        assert score_alignment(log_post, alignment, PHONE_INDEX).phones == []

    def test_skips_implausibly_short_phones(self) -> None:
        log_post = posteriors(50)
        alignment = Alignment(phones=[aligned("k", 0.0, 0.005)], aligner="test")

        assert score_alignment(log_post, alignment, PHONE_INDEX).phones == []

    def test_marks_results_unreliable_when_alignment_was_poor(self) -> None:
        """Frame boundaries from a bad alignment make GOP noise wearing a
        number's clothes. The PPI must know not to trust it."""
        log_post = posteriors(50, confident_phone=PHONE_INDEX["k"])
        alignment = Alignment(
            phones=[aligned("k", 0.0, 0.2)],
            aligner="test",
            score=MIN_ALIGNMENT_SCORE - 0.01,
        )

        assert score_alignment(log_post, alignment, PHONE_INDEX).reliable is False

    def test_a_confident_correct_utterance_scores_near_zero(self) -> None:
        log_post = posteriors(60, confident_phone=PHONE_INDEX["k"])
        alignment = Alignment(
            phones=[aligned("k", 0.0, 0.4), aligned("k", 0.4, 0.8)],
            aligner="test",
        )

        result = score_alignment(log_post, alignment, PHONE_INDEX)

        assert result.phrase_gop == pytest.approx(0.0, abs=1e-9)
        assert result.problem_phones == []


class TestGopToPercent:
    def test_is_bounded_and_monotonic(self) -> None:
        values = [gop_to_percent(g) for g in (0.0, -1.0, -4.0, -20.0)]

        assert values[0] == pytest.approx(100.0)
        assert values == sorted(values, reverse=True)
        assert all(0.0 <= value <= 100.0 for value in values)

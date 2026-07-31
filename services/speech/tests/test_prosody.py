"""Prosody measurement.

These are measurements, not judgements, and the tests are written to hold that
line: they assert that the numbers describe the signal, and that no threshold in
the module encodes an opinion about how a person ought to speak.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline import prosody
from pipeline.prosody import MIN_PAUSE_SECONDS, SAMPLE_RATE, analyse
from tests.conftest import requires_librosa


def tone(seconds: float, frequency: float = 180.0, amplitude: float = 0.3) -> np.ndarray:
    t = np.linspace(0, seconds, int(seconds * SAMPLE_RATE), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.float32)


def utterance(*parts: np.ndarray) -> np.ndarray:
    return np.concatenate(parts).astype(np.float32)


@requires_librosa
class TestPauseDetection:
    def test_finds_a_pause_between_two_stretches_of_speech(self) -> None:
        features = analyse(utterance(tone(1.0), silence(0.8), tone(1.0)))

        assert features.pause_count == 1
        assert features.longest_pause_seconds == pytest.approx(0.8, abs=0.1)

    def test_a_short_closure_is_not_a_pause(self) -> None:
        """40 ms is the gap inside a stop consonant. Calling it a pause would be
        measuring phonetics and reporting it as hesitation."""
        features = analyse(utterance(tone(1.0), silence(0.04), tone(1.0)))
        assert features.pause_count == 0

    def test_leading_and_trailing_silence_are_not_pauses(self) -> None:
        """That is recording latency and the learner reaching for the stop
        control. Counting it penalises exactly the people who take longest to
        reach a button — which is the opposite of what this product is for."""
        features = analyse(utterance(silence(1.5), tone(1.0), silence(2.0)))
        assert features.pause_count == 0

    def test_counts_several_pauses_separately(self) -> None:
        features = analyse(
            utterance(tone(0.6), silence(0.5), tone(0.6), silence(0.5), tone(0.6))
        )
        assert features.pause_count == 2

    def test_pause_ratio_reflects_the_proportion_of_silence(self) -> None:
        features = analyse(utterance(tone(1.0), silence(1.0), tone(1.0)))
        assert features.pause_ratio == pytest.approx(1 / 3, abs=0.1)

    def test_the_pause_threshold_is_a_detection_boundary_not_a_quality_one(self) -> None:
        """There is no 'too long' anywhere in this module. A long pause is
        reported as a long pause and nothing in the pipeline treats it as bad."""
        from pathlib import Path

        source = Path(prosody.__file__).read_text(encoding="utf-8").lower()

        for word in ("too long", "excessive", "too slow", "too fast", "acceptable range"):
            assert word not in source, f"prosody encodes a judgement: {word!r}"

        assert MIN_PAUSE_SECONDS == 0.25


@requires_librosa
class TestSpeakingRuns:
    def test_splits_speech_into_runs_at_the_pauses(self) -> None:
        features = analyse(utterance(tone(0.8), silence(0.5), tone(0.8)))

        assert len(features.speaking_runs_seconds) == 2
        for run in features.speaking_runs_seconds:
            assert run == pytest.approx(0.8, abs=0.15)

    def test_an_unbroken_utterance_is_one_run(self) -> None:
        assert len(analyse(tone(2.0)).speaking_runs_seconds) == 1


@requires_librosa
class TestRates:
    def test_rates_are_none_without_a_word_count(self) -> None:
        """A guessed word count produces a confidently wrong rate, and a wrong
        rate that enters a baseline corrupts every later comparison to it."""
        features = analyse(tone(2.0))

        assert features.speech_rate_wpm is None
        assert features.articulation_rate_wpm is None

    def test_speech_rate_counts_the_whole_utterance(self) -> None:
        features = analyse(utterance(tone(1.0), silence(1.0), tone(1.0)), word_count=6)
        assert features.speech_rate_wpm == pytest.approx(6 / 3 * 60, rel=0.1)

    def test_articulation_rate_excludes_pauses_and_so_is_higher(self) -> None:
        features = analyse(utterance(tone(1.0), silence(1.0), tone(1.0)), word_count=6)

        assert features.articulation_rate_wpm is not None
        assert features.articulation_rate_wpm > features.speech_rate_wpm


@requires_librosa
class TestVoiceAndEnergy:
    def test_a_periodic_signal_is_measured_as_voiced(self) -> None:
        features = analyse(tone(1.5, frequency=150.0))
        assert features.voiced_ratio > 0.5

    def test_pitch_is_tracked_within_the_search_range(self) -> None:
        features = analyse(tone(1.5, frequency=150.0))

        assert features.f0_mean_hz is not None
        assert 100 < features.f0_mean_hz < 220
        assert features.f0_backend in {"praat", "pyin"}

    def test_louder_speech_measures_as_louder(self) -> None:
        quiet = analyse(tone(1.5, amplitude=0.05))
        loud = analyse(tone(1.5, amplitude=0.6))

        assert loud.energy_mean > quiet.energy_mean

    def test_silence_is_measured_rather_than_refused(self) -> None:
        """A learner who pressed record and said nothing has produced a real
        attempt, and the honest answer is a result full of zeroes."""
        features = analyse(silence(2.0))

        assert features.duration_seconds == pytest.approx(2.0, abs=0.01)
        assert features.voiced_ratio == 0.0
        assert features.pause_count == 0
        assert features.f0_mean_hz is None

    def test_quiet_speech_is_not_mistaken_for_silence(self) -> None:
        """Reduced loudness is a characteristic of several dysarthrias. An
        absolute silence floor would classify a quiet learner's whole utterance
        as one long pause."""
        features = analyse(tone(2.0, amplitude=0.02))
        assert features.pause_ratio < 0.2


@requires_librosa
class TestOutputContract:
    def test_every_numeric_field_is_finite(self) -> None:
        features = analyse(utterance(tone(0.7), silence(0.4), tone(0.7)), word_count=4)

        for name, value in vars(features).items():
            if isinstance(value, float):
                assert np.isfinite(value), f"{name} is not finite"

    def test_is_deterministic(self) -> None:
        signal = utterance(tone(0.8), silence(0.4), tone(0.8))
        assert analyse(signal, word_count=5) == analyse(signal, word_count=5)

    def test_availability_is_probed_not_assumed(self) -> None:
        assert isinstance(prosody.is_available(), bool)

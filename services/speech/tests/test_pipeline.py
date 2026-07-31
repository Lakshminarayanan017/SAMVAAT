"""Preprocessing, phonemisation and capability reporting."""

from __future__ import annotations

import io

import numpy as np
import pytest

from pipeline import g2p
from pipeline.backends import uniform_alignment
from pipeline.gop import score_alignment
from pipeline.preprocess import (
    MAX_DURATION_SECONDS,
    TARGET_SAMPLE_RATE,
    AudioRejected,
    normalise,
    preprocess,
)
from pipeline.runner import capabilities


def wav_bytes(
    seconds: float,
    sample_rate: int = TARGET_SAMPLE_RATE,
    amplitude: float = 0.3,
) -> bytes:
    import soundfile as sf

    t = np.linspace(0, seconds, int(seconds * sample_rate), endpoint=False)
    signal = (amplitude * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

    buffer = io.BytesIO()
    sf.write(buffer, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


class TestPreprocess:
    def test_accepts_valid_audio(self) -> None:
        samples = preprocess(wav_bytes(1.0))
        assert samples.dtype == np.float32
        assert len(samples) == TARGET_SAMPLE_RATE

    def test_rejects_the_wrong_sample_rate_rather_than_resampling(self) -> None:
        """Quietly upsampling 8 kHz telephone audio would produce plausible GOP
        scores from spectral detail that was never recorded — a confidently
        wrong number, which is worse than an error."""
        with pytest.raises(AudioRejected, match="8000 Hz"):
            preprocess(wav_bytes(1.0, sample_rate=8_000))

    def test_rejects_audio_that_is_too_short(self) -> None:
        with pytest.raises(AudioRejected, match="too short"):
            preprocess(wav_bytes(0.05))

    def test_rejects_audio_beyond_the_processing_ceiling(self) -> None:
        with pytest.raises(AudioRejected, match="too long"):
            preprocess(wav_bytes(MAX_DURATION_SECONDS + 1))

    def test_rejection_carries_a_message_written_for_a_learner(self) -> None:
        with pytest.raises(AudioRejected) as caught:
            preprocess(wav_bytes(0.05))

        message = caught.value.learner_message
        assert "did not hear" in message
        # Never blames the person, never mentions sample rates or codecs.
        assert not any(word in message.lower() for word in ("invalid", "error", "failed", "hz"))


class TestNormalise:
    def test_scales_to_the_target_peak(self) -> None:
        quiet = (np.sin(np.linspace(0, 10, 1000)) * 0.05).astype(np.float32)
        assert float(np.max(np.abs(normalise(quiet)))) == pytest.approx(0.95, abs=1e-3)

    def test_leaves_silence_alone_rather_than_amplifying_noise(self) -> None:
        silence = np.zeros(1000, dtype=np.float32)
        assert np.array_equal(normalise(silence), silence)

    def test_preserves_relative_dynamics(self) -> None:
        """Peak normalisation, not loudness normalisation: the pause and energy
        structure prosody measures must survive untouched."""
        signal = np.concatenate(
            [np.full(500, 0.1), np.full(500, 0.5)],
        ).astype(np.float32)

        result = normalise(signal)
        assert result[600] / result[100] == pytest.approx(5.0, rel=1e-4)


class TestG2p:
    def test_is_available(self) -> None:
        assert g2p.is_available() is True

    def test_phonemises_a_phrase(self) -> None:
        phones = g2p.phonemise("Good morning.")
        assert [p.symbol for p in phones] == ["G", "UH", "D", "M", "AO", "R", "N", "IH", "NG"]

    def test_strips_stress_by_default(self) -> None:
        """Scoring lexical stress would penalise regional accent and many speech
        differences under the guise of pronunciation. Stress is prosody (M7)."""
        phones = g2p.phonemise("Could you please repeat that?")
        assert all(not p.symbol[-1].isdigit() for p in phones)

    def test_keeps_stress_when_asked(self) -> None:
        assert any(p.symbol[-1].isdigit() for p in g2p.phonemise("Good morning.", keep_stress=True))

    def test_tags_each_phone_with_its_word(self) -> None:
        """Word indices are what let a score point at *which word* was hard,
        rather than at a bare phoneme the learner cannot locate."""
        phones = g2p.phonemise("Good morning.")
        assert g2p.word_count(phones) == 2
        assert {p.symbol for p in phones if p.word_index == 0} == {"G", "UH", "D"}

    def test_trailing_punctuation_does_not_create_a_phantom_word(self) -> None:
        assert g2p.word_count(g2p.phonemise("Hello!")) == 1

    def test_produces_the_string_form_stored_in_the_content_bank(self) -> None:
        assert g2p.phoneme_string("Good morning.") == "G UH D M AO R N IH NG"

    def test_is_deterministic(self) -> None:
        text = "I am from the packaging team."
        assert g2p.phoneme_string(text) == g2p.phoneme_string(text)


class TestCapabilities:
    def test_reports_only_what_is_actually_installed(self) -> None:
        result = capabilities()

        assert set(result) == {
            "asr",
            "forced_alignment",
            "gop",
            "prosody",
            "disfluency",
            "personalised_asr",
            "ppi",
        }
        assert all(isinstance(value, bool) for value in result.values())

    def test_gop_is_never_claimed_without_an_aligner(self) -> None:
        result = capabilities()
        if not result["forced_alignment"]:
            assert result["gop"] is False

    def test_stages_needing_a_trained_model_are_false(self) -> None:
        """disfluency and ppi require the M7 classifier, which has not been
        trained. Reporting them true would leave a learner on a spinner."""
        result = capabilities()
        assert result["disfluency"] is False
        assert result["ppi"] is False


class TestUniformAlignmentFallback:
    def test_spreads_phones_across_the_utterance(self) -> None:
        phones = g2p.phonemise("Good morning.")
        alignment = uniform_alignment(phones, duration_seconds=1.0)

        assert len(alignment.phones) == len(phones)
        assert alignment.phones[0].start_seconds == 0.0
        assert alignment.phones[-1].end_seconds == pytest.approx(1.0)

    def test_is_scored_zero_so_derived_results_are_marked_unreliable(self) -> None:
        """It exists to exercise the downstream shape, never to produce a score
        anyone acts on."""
        phones = g2p.phonemise("Good morning.")
        alignment = uniform_alignment(phones, duration_seconds=1.0)

        assert alignment.score == 0.0

        inventory = {p.symbol: i for i, p in enumerate(phones)}
        posteriors = np.log(np.full((50, len(inventory)), 1 / len(inventory)))

        assert score_alignment(posteriors, alignment, inventory).reliable is False

    def test_handles_an_empty_phone_list(self) -> None:
        assert uniform_alignment([], 1.0).phones == []

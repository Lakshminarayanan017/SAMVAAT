"""Audio preprocessing.

The client already delivers 16 kHz mono WAV, so this stage is a guard rather
than a converter: it verifies what arrived, and refuses what it cannot analyse
honestly.

Refusing loudly matters. A pipeline that quietly resamples 8 kHz telephone audio
up to 16 kHz produces plausible-looking GOP scores from spectral detail that was
never recorded — a confidently wrong number, which is worse than an error.
"""

from __future__ import annotations

import io

import numpy as np

TARGET_SAMPLE_RATE = 16_000

#: Below this there is no speech to analyse.
MIN_DURATION_SECONDS = 0.15

#: A safety ceiling on processing cost, NOT a limit on how long a learner may
#: take. The client imposes no recording limit (Ethics E6); this only bounds
#: what a single request may cost the free-tier host.
MAX_DURATION_SECONDS = 120.0


class AudioRejected(ValueError):
    """The audio cannot be analysed honestly. Carries a learner-facing reason."""

    def __init__(self, reason: str, learner_message: str) -> None:
        self.reason = reason
        self.learner_message = learner_message
        super().__init__(reason)


def load_wav(data: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV bytes to float32 mono samples."""
    import soundfile as sf

    samples, sample_rate = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    # Average rather than pick a channel: a learner on a stereo headset may be
    # much louder on one side, and dropping a channel would halve their signal.
    return samples.mean(axis=1), int(sample_rate)


def preprocess(data: bytes) -> np.ndarray:
    """Validate and normalise an uploaded recording.

    Returns 16 kHz mono float32. Raises `AudioRejected` with a message written
    for the learner rather than for a log file.
    """
    samples, sample_rate = load_wav(data)

    if sample_rate != TARGET_SAMPLE_RATE:
        raise AudioRejected(
            f"expected {TARGET_SAMPLE_RATE} Hz, got {sample_rate} Hz",
            "That recording could not be used. Please try again.",
        )

    duration = len(samples) / sample_rate

    if duration < MIN_DURATION_SECONDS:
        raise AudioRejected(
            f"too short: {duration:.2f}s",
            "I did not hear anything. Please try again.",
        )

    if duration > MAX_DURATION_SECONDS:
        raise AudioRejected(
            f"too long: {duration:.1f}s",
            "That recording is very long. Please try a shorter answer.",
        )

    if not np.isfinite(samples).all():
        raise AudioRejected(
            "non-finite samples",
            "That recording could not be used. Please try again.",
        )

    return normalise(samples)


def normalise(samples: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """Scale to a consistent peak.

    Peak normalisation, not loudness normalisation: it is reversible, it does
    not alter dynamics, and it therefore leaves the pause and energy structure
    that prosody analysis measures exactly as the learner produced it.
    """
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak <= 1e-6:
        return samples
    return (samples * (target_peak / peak)).astype(np.float32)

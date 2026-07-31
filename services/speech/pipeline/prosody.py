"""Prosody analytics (M7, part A).

The music of speech: how fast, how evenly, with what pausing, over what pitch
range, at what energy. All of it is deterministic signal processing — there is no
model here, nothing is trained, and nothing needs a GPU. That is why prosody
lives in the base dependency tier and works on the free CPU host.

WHAT THESE NUMBERS ARE, AND ARE NOT
-----------------------------------
They are raw physical measurements of one recording. They are NOT scores, and
none of them is ever shown to a learner in this form. There is no "normal"
speech rate in this file, no target pause length, no reference F0 range — those
would all be comparisons to a non-disabled speaker, which Ethics E1 forbids.

Every one of these measurements becomes meaningful only after `ppi.py` compares
it to the same learner's own rolling baseline. A learner with dysarthria may
speak at 60 words per minute for their whole life; the number that matters is
whether today's 60 is steadier than their own 58, not how it compares to a
stranger's 150.

PAUSES ARE DATA, NOT DEFECTS
----------------------------
Pause structure is measured because it is the strongest signal of whether a
learner is finding their words comfortably. It is reported. It is never
penalised, and the pause thresholds here are detection boundaries, not quality
boundaries.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

log = logging.getLogger("samvaad.speech.prosody")

SAMPLE_RATE = 16_000

#: Frame geometry, shared with the disfluency extractor so both describe the
#: same silences. 10 ms hop over a 25 ms window is the standard speech frame.
FRAME_LENGTH = 400
HOP_LENGTH = 160

#: A silence must last at least this long to count as a pause rather than as the
#: ordinary closure inside a stop consonant. 250 ms is the conventional boundary
#: in the speech-timing literature; below it you are measuring phonetics, not
#: pausing.
MIN_PAUSE_SECONDS = 0.25

#: Silence detection is relative to the utterance's own energy, not absolute.
#: An absolute floor would classify a quiet speaker as one long pause — and
#: quiet speech is a disability characteristic for several of our personas.
SILENCE_RELATIVE_THRESHOLD = 0.08

#: Absolute floor beneath the relative one, so a recording of pure noise does
#: not have its own noise floor treated as speech.
SILENCE_ABSOLUTE_FLOOR = 0.005

#: Pitch search range, wide enough to cover adult voices of any gender without
#: octave errors. Not a judgement about which pitch is correct.
F0_MIN_HZ = 60.0
F0_MAX_HZ = 400.0


@dataclass(frozen=True)
class ProsodyFeatures:
    """Physical measurements of one utterance.

    Every field is either a measured quantity or None when the measurement could
    not be made. None is used rather than a default, because a default would
    silently enter the learner's baseline as though it had been observed.
    """

    duration_seconds: float

    # ── timing ────────────────────────────────────────────────────────────────
    #: Words per minute over the whole utterance, pauses included.
    speech_rate_wpm: float | None
    #: Words per minute over speaking time only, pauses excluded. This is the
    #: articulation rate: how fast the words come out when they are coming out.
    articulation_rate_wpm: float | None

    # ── pausing ───────────────────────────────────────────────────────────────
    pause_count: int
    total_pause_seconds: float
    mean_pause_seconds: float | None
    longest_pause_seconds: float
    #: Proportion of the utterance spent not speaking.
    pause_ratio: float
    #: Duration of each stretch of continuous speaking, in order. The Personal
    #: Progress Index derives rhythm steadiness from these rather than from
    #: absolute speed — see ADR-0006 for why speed is deliberately not scored.
    speaking_runs_seconds: tuple[float, ...]

    # ── voice ─────────────────────────────────────────────────────────────────
    #: Proportion of frames carrying voicing. Low values indicate breathy or
    #: whispered production, which is common in several dysarthrias.
    voiced_ratio: float
    f0_mean_hz: float | None
    f0_range_hz: float | None
    f0_std_hz: float | None

    # ── energy ────────────────────────────────────────────────────────────────
    energy_mean: float
    energy_std: float
    #: Coefficient of variation of energy over speaking frames. Monotone
    #: delivery has a low value; it is reported, never corrected.
    energy_variation: float

    #: Which backend produced the pitch track, recorded so a score stays
    #: interpretable after a dependency upgrade.
    f0_backend: str = "none"


@lru_cache(maxsize=1)
def is_available() -> bool:
    """Whether prosody analysis can run on this deployment.

    Reported through `/capabilities`. Needs only librosa, which is in the base
    tier, so on a correctly installed host this is always true.
    """
    try:
        import librosa  # noqa: F401

        return True
    except ImportError:  # pragma: no cover - minimal install
        return False


@lru_cache(maxsize=1)
def _pitch_backend() -> str:
    """Praat if available, else librosa's pYIN, else nothing.

    Praat's autocorrelation pitch tracker is the reference implementation in
    phonetics and handles creaky and breathy voice better than pYIN — which
    matters here more than usual, because breathy and creaky phonation are
    exactly what several of our learners produce.
    """
    try:
        import parselmouth  # noqa: F401

        return "praat"
    except ImportError:
        pass

    try:
        import librosa  # noqa: F401

        return "pyin"
    except ImportError:  # pragma: no cover - minimal install
        return "none"


def analyse(
    samples: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    word_count: int | None = None,
) -> ProsodyFeatures:
    """Measure one utterance.

    Args:
        samples: 16 kHz mono float32, already preprocessed.
        sample_rate: kept explicit so the frame maths cannot drift from reality.
        word_count: words in the transcript. Rate fields are None without it —
            a guessed word count would produce a confidently wrong rate, and a
            wrong rate that enters a learner's baseline corrupts every later
            comparison against it.
    """
    import librosa

    samples = np.asarray(samples, dtype=np.float32)
    duration = len(samples) / sample_rate

    if duration <= 0 or not np.any(samples):
        return _empty(duration)

    rms = librosa.feature.rms(
        y=samples, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH
    )[0]
    frame_seconds = HOP_LENGTH / sample_rate

    threshold = max(SILENCE_ABSOLUTE_FLOOR, float(np.max(rms)) * SILENCE_RELATIVE_THRESHOLD)
    silent = rms < threshold

    pauses, speaking_runs = _runs(silent, frame_seconds)
    total_pause = float(sum(pauses))
    speaking_seconds = max(0.0, duration - total_pause)

    rates = _rates(word_count, duration, speaking_seconds)
    f0_mean, f0_range, f0_std, voiced_ratio, backend = _pitch(samples, sample_rate)

    speaking_energy = rms[~silent]
    energy_mean = float(speaking_energy.mean()) if speaking_energy.size else 0.0
    energy_std = float(speaking_energy.std()) if speaking_energy.size else 0.0

    return ProsodyFeatures(
        duration_seconds=duration,
        speech_rate_wpm=rates[0],
        articulation_rate_wpm=rates[1],
        pause_count=len(pauses),
        total_pause_seconds=total_pause,
        mean_pause_seconds=(total_pause / len(pauses)) if pauses else None,
        longest_pause_seconds=max(pauses, default=0.0),
        pause_ratio=total_pause / duration if duration else 0.0,
        speaking_runs_seconds=tuple(speaking_runs),
        voiced_ratio=voiced_ratio,
        f0_mean_hz=f0_mean,
        f0_range_hz=f0_range,
        f0_std_hz=f0_std,
        energy_mean=energy_mean,
        energy_std=energy_std,
        energy_variation=(energy_std / energy_mean) if energy_mean > 1e-9 else 0.0,
        f0_backend=backend,
    )


def _empty(duration: float) -> ProsodyFeatures:
    """Silence. Measured as silence rather than refused, because a learner who
    pressed record and said nothing has produced a real, meaningful attempt."""
    return ProsodyFeatures(
        duration_seconds=duration,
        speech_rate_wpm=None,
        articulation_rate_wpm=None,
        pause_count=0,
        total_pause_seconds=duration,
        mean_pause_seconds=None,
        longest_pause_seconds=duration,
        pause_ratio=1.0 if duration else 0.0,
        speaking_runs_seconds=(),
        voiced_ratio=0.0,
        f0_mean_hz=None,
        f0_range_hz=None,
        f0_std_hz=None,
        energy_mean=0.0,
        energy_std=0.0,
        energy_variation=0.0,
    )


def _rates(
    word_count: int | None,
    duration: float,
    speaking_seconds: float,
) -> tuple[float | None, float | None]:
    if not word_count or duration <= 0:
        return None, None

    speech_rate = word_count / duration * 60.0
    articulation = (word_count / speaking_seconds * 60.0) if speaking_seconds > 0.05 else None
    return speech_rate, articulation


def _runs(silent: np.ndarray, frame_seconds: float) -> tuple[list[float], list[float]]:
    """Split the utterance into pauses and stretches of speaking.

    Leading and trailing silence is excluded from both: it is recording latency
    and the learner reaching for the stop control, not pausing. Counting it
    would penalise exactly the learners who need longest to reach a button.

    Returns `(pauses, speaking_runs)` in seconds. Only silences at or beyond
    `MIN_PAUSE_SECONDS` count as pauses; shorter ones are stop closures and stay
    inside the speaking run they interrupt, because splitting a run on a 40 ms
    plosive would report rhythm that no listener perceives.
    """
    voiced_indices = np.flatnonzero(~silent)
    if voiced_indices.size == 0:
        return [], []

    interior = silent[voiced_indices[0] : voiced_indices[-1] + 1]

    #: (is_silent, frame_count) for each contiguous stretch.
    stretches: list[tuple[bool, int]] = []
    for value in interior:
        is_silent = bool(value)
        if stretches and stretches[-1][0] == is_silent:
            stretches[-1] = (is_silent, stretches[-1][1] + 1)
        else:
            stretches.append((is_silent, 1))

    pauses: list[float] = []
    speaking: list[float] = []
    accumulating = 0.0

    for is_silent, frames in stretches:
        seconds = frames * frame_seconds

        if not is_silent:
            accumulating += seconds
            continue

        if seconds >= MIN_PAUSE_SECONDS:
            pauses.append(seconds)
            if accumulating > 0:
                speaking.append(accumulating)
                accumulating = 0.0
        else:
            # A short closure inside a word. It belongs to the speaking run.
            accumulating += seconds

    if accumulating > 0:
        speaking.append(accumulating)

    return pauses, speaking


def _pitch(
    samples: np.ndarray,
    sample_rate: int,
) -> tuple[float | None, float | None, float | None, float, str]:
    """Pitch statistics over voiced frames, and the voiced ratio."""
    backend = _pitch_backend()

    try:
        if backend == "praat":
            values, voiced_ratio = _pitch_praat(samples, sample_rate)
        elif backend == "pyin":
            values, voiced_ratio = _pitch_pyin(samples, sample_rate)
        else:  # pragma: no cover - minimal install
            return None, None, None, 0.0, "none"
    except Exception as error:  # noqa: BLE001 - a pitch failure must not lose the rest
        log.warning("pitch tracking failed (%s); reporting prosody without F0", error)
        return None, None, None, 0.0, "failed"

    if values.size < 2:
        return None, None, None, voiced_ratio, backend

    return (
        float(np.mean(values)),
        float(np.max(values) - np.min(values)),
        float(np.std(values)),
        voiced_ratio,
        backend,
    )


def _pitch_praat(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    import parselmouth

    sound = parselmouth.Sound(samples.astype(np.float64), sampling_frequency=sample_rate)
    pitch = sound.to_pitch(pitch_floor=F0_MIN_HZ, pitch_ceiling=F0_MAX_HZ)

    track = pitch.selected_array["frequency"]
    voiced = track[track > 0]
    ratio = float(voiced.size / track.size) if track.size else 0.0
    return voiced, ratio


def _pitch_pyin(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, float]:
    import librosa

    f0, voiced_flag, _ = librosa.pyin(
        samples,
        fmin=F0_MIN_HZ,
        fmax=F0_MAX_HZ,
        sr=sample_rate,
        frame_length=FRAME_LENGTH * 4,
        hop_length=HOP_LENGTH,
    )

    voiced = f0[np.isfinite(f0)]
    ratio = float(np.mean(voiced_flag)) if voiced_flag.size else 0.0
    return voiced, ratio

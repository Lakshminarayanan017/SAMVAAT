"""Disfluency detection (M7).

Detects blocks, prolongations, repetitions and interjections in speech.

THE MOST IMPORTANT RULE IN THIS FILE
------------------------------------
A detected disfluency produces a COACHING CUE. It never produces a score
deduction. There is no code path in this module that turns an event into a
penalty, and there must never be one.

P5 (Karthik) has a stammer. If his stammer lowered his score, this product would
be telling him daily that he is failing at not being disabled — which is the
exact harm it exists to prevent (Ethics E1, ADR-0003). The events feed two
things: coaching cues drawn from a speech-language-pathologist strategy library,
and the `fluency` dimension of the Personal Progress Index, which is measured
against the learner's own rolling baseline and is down-weighted for profiles
where disfluency is a disability characteristic rather than a skill gap.

TRAIN/SERVE PARITY
------------------
`extract_features` is imported unchanged by the training notebook. Feature code
that differs between training and inference is one of the most common and most
invisible ML bugs: the model scores well in the notebook and behaves randomly in
production, and nothing errors. One function, one definition, both sides.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

SAMPLE_RATE = 16_000

#: Analysis window. SEP-28k clips are 3 seconds, so the model is trained and
#: served on the same window length.
WINDOW_SECONDS = 3.0

#: Hop between windows when scanning a longer utterance. 1.5 s gives 50% overlap,
#: so an event straddling a boundary is still seen whole by one window.
HOP_SECONDS = 1.5


class DisfluencyType(str, Enum):
    """The five event types, matching the SEP-28k label schema.

    Multi-label, not multi-class: one clip can contain a block AND a
    prolongation, and forcing a single choice would throw away real signal.
    """

    BLOCK = "block"
    PROLONGATION = "prolongation"
    SOUND_REPETITION = "sound_repetition"
    WORD_REPETITION = "word_repetition"
    INTERJECTION = "interjection"


#: Fixed order. The model's output vector is indexed by this, so changing the
#: order silently remaps every prediction — never reorder, only append.
LABELS: list[str] = [t.value for t in DisfluencyType]


@dataclass(frozen=True)
class DisfluencyEvent:
    """One detected event, with the coaching cue that goes with it."""

    type: DisfluencyType
    start_seconds: float
    end_seconds: float
    confidence: float
    strategy: str
    cue: str


# ── The coaching library ─────────────────────────────────────────────────────
# Strategies drawn from standard stuttering-modification and fluency-shaping
# practice. Reviewed by a speech-language pathologist before the pilot — until
# that review, the app labels these as suggestions rather than instruction.
#
# Every cue is phrased as something to TRY, never as something done wrong.

COACHING: dict[DisfluencyType, tuple[str, str]] = {
    DisfluencyType.BLOCK: (
        "easy onset",
        "Try starting that word gently, letting the air move before the sound.",
    ),
    DisfluencyType.PROLONGATION: (
        "light contact",
        "Try touching your lips and tongue lightly on that sound.",
    ),
    DisfluencyType.SOUND_REPETITION: (
        "pull-out",
        "If a sound repeats, try easing out of it slowly rather than pushing through.",
    ),
    DisfluencyType.WORD_REPETITION: (
        "pausing",
        "Try a short pause before that word to give yourself a moment.",
    ),
    DisfluencyType.INTERJECTION: (
        "pausing",
        "A silent pause works just as well as a filler word, and sounds confident.",
    ),
}


def cue_for(event_type: DisfluencyType) -> tuple[str, str]:
    return COACHING[event_type]


# ── Features ─────────────────────────────────────────────────────────────────


#: Names in the exact order `extract_features` returns them. Used by the
#: notebook for feature-importance reporting, and asserted by a test.
FEATURE_NAMES: list[str] = (
    [f"mfcc{i}_mean" for i in range(13)]
    + [f"mfcc{i}_std" for i in range(13)]
    + [f"dmfcc{i}_mean" for i in range(13)]
    + [f"dmfcc{i}_std" for i in range(13)]
    + [
        "rms_mean", "rms_std", "rms_max", "rms_range",
        "zcr_mean", "zcr_std",
        "centroid_mean", "centroid_std",
        "rolloff_mean", "rolloff_std",
        "flatness_mean", "flatness_std",
        "silence_ratio", "longest_silence_s", "silence_run_count",
        "energy_slope", "onset_rate",
    ]
)

N_FEATURES = len(FEATURE_NAMES)

#: Below this RMS a frame counts as silence. Blocks are silent closures, so this
#: threshold is what makes them visible to the classifier at all.
SILENCE_RMS = 0.015


def extract_features(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Turn one analysis window into a fixed-length feature vector.

    IMPORTED UNCHANGED BY THE TRAINING NOTEBOOK. Do not fork this.

    The feature set is deliberately hand-built rather than learned, for the
    first model: it trains in minutes on CPU, it is inspectable when a
    prediction looks wrong, and feature importances tell a speech therapist
    something they can actually read. The wav2vec2 variant in the notebook is
    the upgrade path once this baseline is measured.

    Chosen for what actually distinguishes the five event types:
      * MFCCs and their deltas   - spectral shape and how fast it changes;
                                   prolongations hold shape unusually steady
      * energy statistics        - blocks are silent, interjections are not
      * silence run structure    - the single strongest cue for a block
      * onset rate               - repetitions produce many closely spaced onsets
    """
    import librosa

    samples = np.asarray(samples, dtype=np.float32)
    target_length = int(WINDOW_SECONDS * sample_rate)

    # Fixed length in, fixed length out. Padding rather than resampling: a
    # stretched clip would change the very rhythm we are measuring.
    if len(samples) < target_length:
        samples = np.pad(samples, (0, target_length - len(samples)))
    else:
        samples = samples[:target_length]

    if not np.any(samples):
        return np.zeros(N_FEATURES, dtype=np.float32)

    hop = 160  # 10 ms at 16 kHz
    n_fft = 400  # 25 ms

    mfcc = librosa.feature.mfcc(
        y=samples, sr=sample_rate, n_mfcc=13, n_fft=n_fft, hop_length=hop
    )
    dmfcc = librosa.feature.delta(mfcc)

    rms = librosa.feature.rms(y=samples, frame_length=n_fft, hop_length=hop)[0]
    zcr = librosa.feature.zero_crossing_rate(samples, frame_length=n_fft, hop_length=hop)[0]
    centroid = librosa.feature.spectral_centroid(
        y=samples, sr=sample_rate, n_fft=n_fft, hop_length=hop
    )[0]
    rolloff = librosa.feature.spectral_rolloff(
        y=samples, sr=sample_rate, n_fft=n_fft, hop_length=hop
    )[0]
    flatness = librosa.feature.spectral_flatness(y=samples, n_fft=n_fft, hop_length=hop)[0]

    silent = rms < SILENCE_RMS
    frame_seconds = hop / sample_rate

    features = np.concatenate(
        [
            mfcc.mean(axis=1), mfcc.std(axis=1),
            dmfcc.mean(axis=1), dmfcc.std(axis=1),
            [
                float(rms.mean()), float(rms.std()), float(rms.max()),
                float(rms.max() - rms.min()),
                float(zcr.mean()), float(zcr.std()),
                float(centroid.mean()), float(centroid.std()),
                float(rolloff.mean()), float(rolloff.std()),
                float(flatness.mean()), float(flatness.std()),
                float(silent.mean()),
                _longest_run(silent) * frame_seconds,
                float(_run_count(silent)),
                _energy_slope(rms),
                _onset_rate(samples, sample_rate),
            ],
        ]
    ).astype(np.float32)

    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def _longest_run(mask: np.ndarray) -> int:
    """Longest consecutive True run. The strongest single cue for a block."""
    longest = current = 0
    for value in mask:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def _run_count(mask: np.ndarray) -> int:
    """Number of distinct True runs — many short silences suggest repetition."""
    return int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1))


def _energy_slope(rms: np.ndarray) -> float:
    """Linear trend in energy across the window."""
    if len(rms) < 2:
        return 0.0
    x = np.arange(len(rms), dtype=np.float64)
    return float(np.polyfit(x, rms.astype(np.float64), 1)[0])


def _onset_rate(samples: np.ndarray, sample_rate: int) -> float:
    """Onsets per second. Repetitions produce many closely spaced onsets."""
    import librosa

    onsets = librosa.onset.onset_detect(y=samples, sr=sample_rate, units="time")
    return float(len(onsets) / WINDOW_SECONDS)


def windows(samples: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """Split an utterance into overlapping analysis windows."""
    size = int(WINDOW_SECONDS * sample_rate)
    hop = int(HOP_SECONDS * sample_rate)

    if len(samples) <= size:
        yield 0.0, samples
        return

    for start in range(0, len(samples) - size + 1, hop):
        yield start / sample_rate, samples[start : start + size]


# ── Inference ────────────────────────────────────────────────────────────────


class DisfluencyModel:
    """ONNX wrapper around the trained classifier.

    The model file is produced by training/notebooks/train_disfluency.ipynb and
    dropped into services/speech/artifacts/. It is not in version control:
    weights belong in the model registry, not in git.
    """

    def __init__(self, model_path: str, threshold: float = 0.5) -> None:
        import onnxruntime

        self.session = onnxruntime.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )
        self.threshold = threshold
        self.input_name = self.session.get_inputs()[0].name

    def predict_window(self, samples: np.ndarray) -> dict[str, float]:
        features = extract_features(samples).reshape(1, -1)
        probabilities = self.session.run(None, {self.input_name: features})[0][0]
        return dict(zip(LABELS, (float(p) for p in probabilities), strict=True))

    def detect(self, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> list[DisfluencyEvent]:
        """Scan an utterance and return events, each with its coaching cue.

        Note what this returns: events with cues. Not a score, not a count of
        mistakes, not a fluency percentage. Everything downstream of this
        function receives coaching material.
        """
        events: list[DisfluencyEvent] = []

        for offset, window in windows(samples, sample_rate):
            for label, probability in self.predict_window(window).items():
                if probability < self.threshold:
                    continue

                event_type = DisfluencyType(label)
                strategy, cue = cue_for(event_type)

                events.append(
                    DisfluencyEvent(
                        type=event_type,
                        start_seconds=offset,
                        end_seconds=offset + WINDOW_SECONDS,
                        confidence=probability,
                        strategy=strategy,
                        cue=cue,
                    )
                )

        return events

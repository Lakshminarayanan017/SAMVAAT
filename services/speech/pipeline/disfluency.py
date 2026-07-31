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

import logging
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

import numpy as np

log = logging.getLogger("samvaad.speech.disfluency")

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


@dataclass(frozen=True)
class ModelStatus:
    available: bool
    detail: str


#: Filename per label inside the artefacts directory. This is the exact shape
#: `training/notebooks/train_disfluency.ipynb` produces, and the notebook is the
#: contract with whoever runs the training — so the serving side matches the
#: artefact rather than the other way round.
def model_filename(label: str) -> str:
    return f"disfluency_{label}.onnx"


#: Written alongside the models by the training run. Carries the per-class
#: thresholds, which matter: a single 0.5 threshold across five imbalanced
#: classes collapses the rare ones to "never fires", and the rare one here is
#: `block`, which is the event P5 most needs recognised.
METRICS_FILE = "metrics.json"


@lru_cache(maxsize=1)
def model_status() -> ModelStatus:
    """Is the trained classifier actually present on this host?

    Reported by `/capabilities`, and the answer is "no" on a fresh clone. That
    is deliberate and it is the honest state: the SEP-28k training run is the
    one piece of this system that cannot be produced by writing code, and
    claiming the capability without the weights would leave a learner watching a
    spinner for feedback that is never coming — or worse, seeing invented
    coaching cues about speech nobody analysed.

    See services/speech/training/README.md for the training command, and
    docs/TRAINING_HANDOFF.md for datasets, hardware and expected duration.
    """
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return ModelStatus(False, "onnxruntime not installed (requirements-ml.txt)")

    from service.config import get_settings

    directory = get_settings().artifacts_dir

    missing = [label for label in LABELS if not (directory / model_filename(label)).exists()]
    if missing:
        return ModelStatus(
            False,
            f"no trained classifier in {directory} (missing: {', '.join(missing)}); "
            "see services/speech/training/README.md",
        )

    return ModelStatus(True, _version_from_metrics(directory))


def _version_from_metrics(directory) -> str:
    """A recordable version string for `speech_attempts.model_versions`.

    Uses the training timestamp and macro-F1 from the run itself, so a score
    stays interpretable after a model upgrade: "which model produced this, and
    how good was it" is answerable two years later from the attempt row alone.
    """
    import json

    path = directory / METRICS_FILE
    if not path.exists():
        return "disfluency/unversioned"

    try:
        metrics = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "disfluency/unreadable-metrics"

    trained = str(metrics.get("trained_at", "unknown"))[:10]
    return f"disfluency/{trained}/macro_f1={metrics.get('macro_f1', 0):.3f}"


@lru_cache(maxsize=1)
def load_model() -> DisfluencyModel:
    """The classifier, loaded once and cached.

    Raises rather than returning a stand-in. A stand-in that emitted plausible
    events would put invented coaching cues in front of a learner about speech
    they did not produce, and nothing downstream could tell the difference.
    Callers check `model_status()` first; the runner does, and skips the stage
    with a reason the client can show.
    """
    from service.config import get_settings

    settings = get_settings()
    status = model_status()

    if not status.available:
        raise RuntimeError(f"Disfluency classifier unavailable: {status.detail}")

    log.info("loading disfluency classifier from %s", settings.artifacts_dir)
    return DisfluencyModel(
        settings.artifacts_dir,
        default_threshold=settings.disfluency_threshold,
    )


class DisfluencyModel:
    """ONNX wrapper around the trained classifier.

    One binary classifier per event type, because the task is multi-label: a
    single clip can contain a block AND a prolongation, and forcing one choice
    throws away real signal.

    The artefacts are produced by `training/notebooks/train_disfluency.ipynb`
    and dropped into `services/speech/artifacts/`. They are not in version
    control: weights belong in the model registry, not in git.
    """

    def __init__(self, artifacts_dir, default_threshold: float = 0.5) -> None:
        import json

        import onnxruntime

        options = onnxruntime.SessionOptions()
        # One thread per session. The service runs several requests
        # concurrently on a small CPU host, and letting five sessions each
        # spawn a thread pool turns a 200 ms inference into a scheduling storm.
        options.intra_op_num_threads = 1

        self.sessions = {
            label: onnxruntime.InferenceSession(
                str(artifacts_dir / model_filename(label)),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            for label in LABELS
        }

        self.input_names = {
            label: session.get_inputs()[0].name for label, session in self.sessions.items()
        }

        # Per-class thresholds tuned on the validation split during training.
        # Falling back to one global value is safe but blunt, so the fallback is
        # logged rather than silent.
        self.thresholds = dict.fromkeys(LABELS, default_threshold)

        metrics_path = artifacts_dir / METRICS_FILE
        if metrics_path.exists():
            try:
                tuned = json.loads(metrics_path.read_text(encoding="utf-8")).get("thresholds")
                if isinstance(tuned, dict):
                    self.thresholds.update(
                        {label: float(value) for label, value in tuned.items() if label in LABELS}
                    )
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                log.warning(
                    "could not read tuned thresholds (%s); using %s",
                    error,
                    default_threshold,
                )
        else:
            log.warning(
                "%s not found; using the single default threshold %.2f for all five event "
                "types, which under-detects the rare ones",
                metrics_path,
                default_threshold,
            )

    def predict_window(self, samples: np.ndarray) -> dict[str, float]:
        features = extract_features(samples).reshape(1, -1)

        probabilities: dict[str, float] = {}
        for label, session in self.sessions.items():
            outputs = session.run(None, {self.input_names[label]: features})
            probabilities[label] = _positive_probability(outputs)

        return probabilities

    def detect(self, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> list[DisfluencyEvent]:
        """Scan an utterance and return events, each with its coaching cue.

        Note what this returns: events with cues. Not a score, not a count of
        mistakes, not a fluency percentage. Everything downstream of this
        function receives coaching material.
        """
        events: list[DisfluencyEvent] = []

        for offset, window in windows(samples, sample_rate):
            for label, probability in self.predict_window(window).items():
                if probability < self.thresholds[label]:
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


def _positive_probability(outputs: list) -> float:
    """Pull P(event) out of whatever shape skl2onnx produced.

    Exported scikit-learn classifiers emit `[labels, probabilities]` with
    `zipmap=False`, so the probabilities are the second output and the positive
    class is column 1. Older exports emit only probabilities. Handling both
    means a re-export with a different skl2onnx version does not silently start
    reading the *negative* class — which would invert every prediction and look,
    from the outside, exactly like a badly trained model.
    """
    candidate = outputs[1] if len(outputs) > 1 else outputs[0]
    row = np.asarray(candidate)[0]

    if row.ndim == 0:
        return float(row)
    return float(row[-1]) if row.shape[0] >= 2 else float(row[0])

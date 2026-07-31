"""Disfluency detection.

The feature tests guard train/serve parity: the training notebook imports these
exact functions, so a change here that is not retrained silently invalidates the
model. The coaching tests guard the ethics property, which is the whole reason
this module is shaped the way it is.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.disfluency import (
    COACHING,
    FEATURE_NAMES,
    LABELS,
    N_FEATURES,
    SAMPLE_RATE,
    WINDOW_SECONDS,
    DisfluencyType,
    cue_for,
    extract_features,
    windows,
)
from tests.conftest import requires_librosa


def tone(seconds: float = WINDOW_SECONDS, frequency: float = 180.0, amplitude: float = 0.3):
    t = np.linspace(0, seconds, int(seconds * SAMPLE_RATE), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def with_gap(gap_start: float, gap_end: float):
    """Speech with a silent closure — the acoustic signature of a block."""
    signal = tone()
    signal[int(gap_start * SAMPLE_RATE) : int(gap_end * SAMPLE_RATE)] = 0.0
    return signal


def named(features: np.ndarray) -> dict[str, float]:
    return dict(zip(FEATURE_NAMES, features, strict=True))


# ── The ethics property ───────────────────────────────────────────────────────


class TestCoachingNotPenalty:
    def test_every_event_type_has_a_coaching_cue(self) -> None:
        """No event may exist without something constructive to say about it."""
        for event_type in DisfluencyType:
            strategy, cue = cue_for(event_type)
            assert strategy and cue

    def test_cues_suggest_rather_than_correct(self) -> None:
        """A cue is something to TRY, never something done wrong.

        Ethics E1. P5 has a stammer; language that frames his speech as an error
        is the harm this product exists to prevent.
        """
        blaming = [
            "wrong", "error", "mistake", "fail", "incorrect", "bad",
            "you should", "don't", "avoid", "problem", "fix your",
        ]

        for event_type in DisfluencyType:
            _, cue = cue_for(event_type)
            lower = cue.lower()
            for word in blaming:
                assert word not in lower, f"{event_type.value} cue is blaming: {cue!r}"
            assert "try" in lower or "works just as well" in lower

    def test_the_module_exposes_no_scoring_function(self) -> None:
        """There is no code path from an event to a deduction, and there must
        never be one. This test is the guard on that."""
        import pipeline.disfluency as module

        for name in dir(module):
            lower = name.lower()
            assert not any(
                token in lower for token in ("penalty", "deduct", "score", "fluency_score")
            ), f"{name} looks like scoring; disfluency produces cues, not scores"

    def test_coaching_covers_the_label_set_exactly(self) -> None:
        assert {t.value for t in COACHING} == set(LABELS)


# ── Train/serve parity ────────────────────────────────────────────────────────


class TestFeatureContract:
    """Only the tests that actually call the extractor need the audio tier.

    The label-order and name-count assertions are pure declarations and must run
    on every install: they are what stops someone reordering LABELS and silently
    remapping every prediction the trained model makes.
    """

    def test_label_order_is_fixed(self) -> None:
        """The model's output vector is indexed by this. Reordering silently
        remaps every prediction — append only, never reorder."""
        assert LABELS == [
            "block",
            "prolongation",
            "sound_repetition",
            "word_repetition",
            "interjection",
        ]

    def test_feature_count_matches_the_declared_names(self) -> None:
        assert len(FEATURE_NAMES) == N_FEATURES
        assert len(set(FEATURE_NAMES)) == N_FEATURES, "duplicate feature name"

    @requires_librosa
    def test_vector_shape_is_stable(self) -> None:
        assert extract_features(tone()).shape == (N_FEATURES,)

    @requires_librosa
    def test_output_is_always_finite(self) -> None:
        """NaN in a feature vector poisons training silently."""
        for signal in [tone(), np.zeros(3 * SAMPLE_RATE, np.float32), with_gap(0.5, 2.5)]:
            assert np.isfinite(extract_features(signal)).all()

    @requires_librosa
    def test_silence_returns_zeros_rather_than_failing(self) -> None:
        result = extract_features(np.zeros(3 * SAMPLE_RATE, dtype=np.float32))
        assert result.shape == (N_FEATURES,)
        assert not result.any()

    @requires_librosa
    def test_short_input_is_padded_not_stretched(self) -> None:
        """Stretching would change the very rhythm the model measures."""
        assert extract_features(tone(0.5)).shape == (N_FEATURES,)

    @requires_librosa
    def test_long_input_is_truncated_to_the_window(self) -> None:
        assert extract_features(tone(10.0)).shape == (N_FEATURES,)

    @requires_librosa
    def test_is_deterministic(self) -> None:
        signal = with_gap(1.0, 1.8)
        assert np.array_equal(extract_features(signal), extract_features(signal))


# ── Does the feature set actually see the events? ─────────────────────────────


@requires_librosa
class TestDiscrimination:
    def test_silence_features_detect_a_block(self) -> None:
        """A block IS a silent closure. If these features cannot see one, the
        model would have to reach the label some other way — a shortcut that
        will not survive contact with a real learner."""
        blocked = named(extract_features(with_gap(1.0, 1.8)))
        fluent = named(extract_features(tone()))

        assert blocked["longest_silence_s"] == pytest.approx(0.8, abs=0.1)
        assert fluent["longest_silence_s"] < 0.05
        assert blocked["silence_ratio"] > fluent["silence_ratio"]

    def test_repeated_gaps_raise_the_run_count(self) -> None:
        """Many short silences suggest repetition rather than a single block."""
        signal = tone()
        for start in (0.4, 0.9, 1.4, 1.9):
            signal[int(start * SAMPLE_RATE) : int((start + 0.1) * SAMPLE_RATE)] = 0.0

        repeated = named(extract_features(signal))
        single = named(extract_features(with_gap(1.0, 1.8)))

        assert repeated["silence_run_count"] > single["silence_run_count"]

    def test_loudness_change_shows_in_the_energy_features(self) -> None:
        quiet = named(extract_features(tone(amplitude=0.05)))
        loud = named(extract_features(tone(amplitude=0.6)))

        assert loud["rms_mean"] > quiet["rms_mean"]


class TestArtefactContract:
    """The serving code must load exactly what the training notebook writes.

    This is the other half of train/serve parity, and the half that is usually
    discovered on the day the weights arrive: the features matched, and then
    nothing could open the files. The notebook is the contract — whoever runs
    training follows it — so the serving side is what must match.
    """

    def _notebook_source(self) -> str:
        import json
        from pathlib import Path

        notebook = (
            Path(__file__).resolve().parents[1]
            / "training"
            / "notebooks"
            / "train_disfluency.ipynb"
        )
        cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
        return "\n".join("".join(cell["source"]) for cell in cells)

    def test_the_loader_expects_the_filenames_the_notebook_writes(self) -> None:
        from pipeline.disfluency import model_filename

        source = self._notebook_source()

        # The notebook writes `disfluency_{label}.onnx` in a loop over labels.
        assert "disfluency_{label}.onnx" in source
        for label in LABELS:
            assert model_filename(label) == f"disfluency_{label}.onnx"

    def test_the_loader_reads_the_metrics_file_the_notebook_writes(self) -> None:
        from pipeline.disfluency import METRICS_FILE

        assert METRICS_FILE in self._notebook_source()

    def test_the_notebook_records_per_class_thresholds(self) -> None:
        """A single 0.5 across five imbalanced classes silences the rare ones,
        and the rarest is `block` — the event P5 most needs recognised."""
        assert "'thresholds': thresholds" in self._notebook_source()

    def test_capability_is_false_without_the_artefacts(self) -> None:
        """Honest by default on a fresh clone. Claiming the capability without
        the weights would show a learner invented cues about speech nobody
        analysed."""
        from pipeline.disfluency import model_status

        status = model_status()
        assert isinstance(status.available, bool)
        if not status.available:
            assert "training" in status.detail or "onnxruntime" in status.detail


class TestWindows:
    def test_a_short_utterance_yields_one_window(self) -> None:
        assert len(list(windows(tone(2.0)))) == 1

    def test_a_long_utterance_is_split_with_overlap(self) -> None:
        """50% overlap, so an event straddling a boundary is still seen whole
        by one window."""
        produced = list(windows(np.zeros(10 * SAMPLE_RATE, dtype=np.float32)))

        assert len(produced) > 1
        offsets = [offset for offset, _ in produced]
        assert offsets == sorted(offsets)
        assert offsets[1] - offsets[0] == pytest.approx(WINDOW_SECONDS / 2, abs=0.01)

    def test_every_window_is_the_declared_length(self) -> None:
        for _, window in windows(np.zeros(10 * SAMPLE_RATE, dtype=np.float32)):
            assert len(window) == int(WINDOW_SECONDS * SAMPLE_RATE)

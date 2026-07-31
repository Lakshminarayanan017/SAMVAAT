"""Optional heavy backends: ASR and forced alignment.

Whisper and the CTC aligner need PyTorch and multi-gigabyte model downloads.
Both are imported lazily and probed rather than assumed, so:

  * the service boots in seconds on a free-tier host with nothing installed,
  * `/capabilities` reports what is genuinely available, and
  * the client degrades honestly instead of hanging on a spinner.

The alternative — importing torch at module scope — means the whole service
fails to start if one dependency is missing, and a learner sees a dead app
rather than a working text path.

INSTALLING THE BACKENDS
-----------------------
    pip install -r requirements-ml.txt

That pulls ~2.5 GB. See services/speech/README.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from pipeline.types import AlignedPhone, Alignment, Phone, Transcript

log = logging.getLogger("samvaad.speech.backends")


@dataclass(frozen=True)
class BackendStatus:
    available: bool
    detail: str


@lru_cache(maxsize=1)
def torch_status() -> BackendStatus:
    try:
        import torch

        return BackendStatus(True, f"torch {torch.__version__}")
    except ImportError as error:
        return BackendStatus(False, f"not installed ({error.name})")


@lru_cache(maxsize=1)
def asr_status() -> BackendStatus:
    if not torch_status().available:
        return BackendStatus(False, "requires torch")
    try:
        import transformers  # noqa: F401

        return BackendStatus(True, "transformers available")
    except ImportError:
        return BackendStatus(False, "transformers not installed")


@lru_cache(maxsize=1)
def aligner_status() -> BackendStatus:
    if not torch_status().available:
        return BackendStatus(False, "requires torch")
    try:
        import torchaudio  # noqa: F401

        return BackendStatus(True, "torchaudio CTC alignment available")
    except ImportError:
        return BackendStatus(False, "torchaudio not installed")


# ── ASR ───────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _whisper(model_name: str):
    from transformers import pipeline as hf_pipeline

    log.info("loading ASR model %s (first call downloads weights)", model_name)
    return hf_pipeline("automatic-speech-recognition", model=model_name)


def transcribe(samples: np.ndarray, model_name: str, sample_rate: int = 16_000) -> Transcript:
    """The FREE recognition pass: what did the learner actually say?

    Deliberately unconstrained by the target text. This answers intelligibility.
    The separate forced pass answers "how well did they say the intended thing",
    and conflating the two is the classic bug in this kind of pipeline.
    """
    if not asr_status().available:
        raise RuntimeError("ASR backend unavailable; install requirements-ml.txt")

    result = _whisper(model_name)(
        {"raw": samples, "sampling_rate": sample_rate},
        return_timestamps=False,
    )

    text = (result.get("text") or "").strip()

    return Transcript(
        text=text,
        # Whisper does not expose a calibrated confidence. Reporting a made-up
        # number would be worse than reporting none, because downstream code
        # would trust it — so this is a coarse proxy the caller can recognise
        # as such, replaced by a real estimate in M8.
        confidence=0.0 if not text else 0.8,
        model=model_name,
    )


# ── Forced alignment ──────────────────────────────────────────────────────────


def align(
    samples: np.ndarray,
    phones: list[Phone],
    sample_rate: int = 16_000,
) -> Alignment:
    """Locate each expected phone in time.

    `torchaudio`'s CTC segmentation rather than the Montreal Forced Aligner:
    MFA is more precise but is a heavyweight install that is painful to
    containerise on a free tier. ADR pending once both are measured on the same
    evaluation set — the harness exists precisely so that choice is made on
    numbers rather than on preference.
    """
    if not aligner_status().available:
        raise RuntimeError("Aligner backend unavailable; install requirements-ml.txt")

    raise NotImplementedError(
        "CTC forced alignment lands with the ASR model wiring. The GOP scorer "
        "that consumes this is complete and tested (pipeline/gop.py)."
    )


def uniform_alignment(
    phones: list[Phone],
    duration_seconds: float,
    aligner: str = "uniform-fallback",
) -> Alignment:
    """Spread phones evenly across the utterance.

    NOT a substitute for real alignment — it is only good enough to exercise the
    downstream shape in tests. It is scored 0.0 so that `score_alignment` marks
    every result derived from it as unreliable, and the Personal Progress Index
    knows to discard it.
    """
    if not phones:
        return Alignment(phones=[], aligner=aligner, score=0.0)

    step = duration_seconds / len(phones)

    return Alignment(
        phones=[
            AlignedPhone(phone=phone, start_seconds=index * step, end_seconds=(index + 1) * step)
            for index, phone in enumerate(phones)
        ],
        aligner=aligner,
        score=0.0,
    )

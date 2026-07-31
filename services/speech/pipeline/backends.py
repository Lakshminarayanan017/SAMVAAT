"""Optional heavy backends: ASR, phoneme posteriors and forced alignment.

Whisper, wav2vec2 and the CTC aligner need PyTorch and multi-gigabyte model
downloads. Everything here is imported lazily and probed rather than assumed, so:

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

WHY A PHONEME MODEL AND NOT AN ASR MODEL FOR ALIGNMENT
------------------------------------------------------
GOP needs per-phoneme posteriors. A word-level ASR head emits characters or
word-pieces, and deriving phoneme confidence from those means inventing an
intermediate step that was never trained. `wav2vec2-lv-60-espeak-cv-ft` emits IPA
phoneme posteriors directly, which is exactly the quantity the GOP definition is
written over — so the maths in `gop.py` scores what the model actually predicted
rather than a reconstruction of it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from pipeline.g2p import arpabet_to_ipa
from pipeline.types import AlignedPhone, Alignment, Phone, Transcript

log = logging.getLogger("samvaad.speech.backends")

#: Phoneme-level CTC acoustic model. Multilingual, fine-tuned for phoneme
#: recognition, and small enough to run on a free CPU host at roughly real time.
PHONEME_MODEL = "facebook/wav2vec2-lv-60-espeak-cv-ft"

#: wav2vec2 emits one frame per 20 ms at 16 kHz.
FRAME_SHIFT_SECONDS = 0.02


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
    """Forced alignment needs torchaudio's CTC aligner and a phoneme model."""
    if not torch_status().available:
        return BackendStatus(False, "requires torch")

    try:
        import torchaudio.functional as F
    except ImportError:
        return BackendStatus(False, "torchaudio not installed")

    if not hasattr(F, "forced_align"):
        return BackendStatus(False, "torchaudio too old for forced_align (needs >= 2.1)")

    if not asr_status().available:
        return BackendStatus(False, "requires transformers for the phoneme model")

    return BackendStatus(True, "torchaudio CTC alignment over wav2vec2 phoneme posteriors")


@lru_cache(maxsize=1)
def adapter_status() -> BackendStatus:
    """Per-learner ASR adapters (M8).

    Available means the machinery can load an adapter, not that any learner has
    one. Whether a specific learner is personalised is a property of their
    speaker profile, not of the deployment.
    """
    if not asr_status().available:
        return BackendStatus(False, "requires transformers")

    try:
        import peft  # noqa: F401
    except ImportError:
        return BackendStatus(False, "peft not installed (requirements-ml.txt)")

    from service.config import get_settings

    directory = get_settings().adapters_dir
    if directory is None:
        return BackendStatus(False, "adapters_dir not configured")
    if not directory.exists():
        return BackendStatus(False, f"adapters_dir {directory} does not exist")

    return BackendStatus(True, f"adapters from {directory}")


# ── ASR ───────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=2)
def _whisper(model_name: str):
    from transformers import pipeline as hf_pipeline

    log.info("loading ASR model %s (first call downloads weights)", model_name)
    return hf_pipeline("automatic-speech-recognition", model=model_name)


def transcribe(
    samples: np.ndarray,
    model_name: str,
    sample_rate: int = 16_000,
    bias_phrases: tuple[str, ...] = (),
    speaker_id: str | None = None,
) -> Transcript:
    """The FREE recognition pass: what did the learner actually say?

    Deliberately unconstrained by the target text as a *transcript* — this
    answers intelligibility. The separate forced pass answers "how well did they
    say the intended thing", and conflating the two is the classic bug in this
    kind of pipeline.

    `bias_phrases` nudges decoding toward the vocabulary we expect without
    forcing it. That is M8 stage (a): nearly free, no GPU, and the single
    largest accuracy win available on atypical speech in a closed-vocabulary
    drill. It biases; it does not constrain, so a learner who says something
    else is still transcribed as having said something else.
    """
    if not asr_status().available:
        raise RuntimeError("ASR backend unavailable; install requirements-ml.txt")

    pipe = _adapted_pipeline(model_name, speaker_id)

    generate_kwargs: dict[str, object] = {}
    prompt = _bias_prompt(bias_phrases)
    if prompt:
        generate_kwargs["prompt_ids"] = pipe.tokenizer.get_prompt_ids(
            prompt, return_tensors="pt"
        ).to(pipe.model.device)

    result = pipe(
        {"raw": samples, "sampling_rate": sample_rate},
        return_timestamps=False,
        generate_kwargs=generate_kwargs or None,
    )

    text = (result.get("text") or "").strip()
    # Whisper echoes the prompt back into the transcript on some versions.
    # Stripping it is not cosmetic: leaving it in would make intelligibility
    # read as perfect for a learner who said nothing at all.
    if prompt and text.startswith(prompt):
        text = text[len(prompt) :].strip()

    return Transcript(
        text=text,
        # Whisper does not expose a calibrated confidence. Reporting a made-up
        # number would be worse than reporting none, because downstream code
        # would trust it — so this is a coarse proxy the caller can recognise
        # as such, replaced by a real estimate in M8's adapter evaluation.
        confidence=0.0 if not text else 0.8,
        model=model_name,
        adapter=speaker_id if speaker_id and adapter_status().available else None,
    )


def _bias_prompt(phrases: tuple[str, ...]) -> str:
    """Turn the expected phrases into a decoder prompt.

    Kept short. A long prompt eats the context window and starts to *steer* the
    transcript rather than bias it, at which point a learner who mispronounced a
    word gets credited with saying it correctly — the pipeline would be lying to
    protect their feelings, which is not the same thing as being fair to them.
    """
    unique = [phrase.strip() for phrase in phrases if phrase and phrase.strip()]
    return " ".join(unique)[:200]


def _adapted_pipeline(model_name: str, speaker_id: str | None):
    """The base pipeline, with this learner's adapter applied if they have one.

    Falls back to base ASR silently on any adapter problem. A missing adapter
    must never become a failed attempt: the learner recorded something, and the
    right response is a slightly worse transcript, not an error screen.
    """
    pipe = _whisper(model_name)

    if not speaker_id or not adapter_status().available:
        return pipe

    try:
        from pipeline.adapters import apply_adapter

        return apply_adapter(pipe, speaker_id)
    except Exception as error:  # noqa: BLE001 - degrade to base ASR, never fail
        log.warning("adapter for %s could not be applied (%s); using base ASR", speaker_id, error)
        return pipe


# ── Phoneme posteriors and forced alignment ───────────────────────────────────


@lru_cache(maxsize=1)
def _phoneme_model():
    """The phoneme CTC model and its vocabulary.

    Returns `(model, processor, phone_to_index)`. The vocabulary is IPA, which
    is why `g2p` exposes an ARPAbet-to-IPA map: CMUdict speaks ARPAbet and this
    model speaks IPA, and a silent mismatch between them would align every
    utterance against the wrong targets and produce confident nonsense.
    """
    import torch
    from transformers import AutoModelForCTC, AutoProcessor

    log.info("loading phoneme model %s (first call downloads weights)", PHONEME_MODEL)
    processor = AutoProcessor.from_pretrained(PHONEME_MODEL)
    model = AutoModelForCTC.from_pretrained(PHONEME_MODEL)
    model.eval()

    vocabulary = processor.tokenizer.get_vocab()

    torch.set_num_threads(max(1, torch.get_num_threads()))
    return model, processor, vocabulary


def phone_inventory() -> dict[str, int] | None:
    """ARPAbet symbol -> column in the posterior matrix.

    None when the acoustic model is unavailable. `gop.score_alignment` skips any
    phone absent from this map rather than scoring it zero, because a zero reads
    as a perfect pronunciation of a sound the model cannot even represent.
    """
    if not aligner_status().available:
        return None

    _, _, vocabulary = _phoneme_model()

    inventory: dict[str, int] = {}
    for arpabet, ipa in arpabet_to_ipa().items():
        index = vocabulary.get(ipa)
        if index is not None:
            inventory[arpabet] = index

    return inventory


def posteriors(samples: np.ndarray, sample_rate: int = 16_000) -> np.ndarray:
    """Frame-level log-posteriors over the phoneme vocabulary, (frames, phones)."""
    import torch

    model, processor, _ = _phoneme_model()

    inputs = processor(
        samples, sampling_rate=sample_rate, return_tensors="pt", padding=True
    )

    with torch.inference_mode():
        logits = model(inputs.input_values).logits[0]

    return torch.log_softmax(logits, dim=-1).cpu().numpy()


def align(
    samples: np.ndarray,
    phones: list[Phone],
    sample_rate: int = 16_000,
) -> tuple[Alignment, np.ndarray | None]:
    """Locate each expected phone in time, and return the posteriors behind it.

    `torchaudio`'s CTC forced alignment rather than the Montreal Forced Aligner:
    MFA is more precise but is a heavyweight install that is painful to
    containerise on a free tier, and the eval harness measures the difference
    rather than assuming it (ADR-0007).

    Returns `(alignment, log_posteriors)` so the caller can score GOP over the
    exact frames the alignment used. Handing back only the alignment would force
    a second forward pass, doubling the cost of the most expensive stage.
    """
    if not aligner_status().available:
        raise RuntimeError("Aligner backend unavailable; install requirements-ml.txt")

    if not phones:
        return Alignment(phones=[], aligner="ctc-wav2vec2", score=0.0), None

    import torch
    import torchaudio.functional as F

    log_posteriors = posteriors(samples, sample_rate)
    inventory = phone_inventory() or {}

    # Phones the acoustic model has no output unit for are dropped rather than
    # aligned against an arbitrary column, which would place a real boundary at
    # a meaningless time and corrupt every span after it.
    known = [
        (phone, index)
        for phone in phones
        if (index := inventory.get(phone.symbol)) is not None
    ]

    if not known:
        # Every expected phone is outside the model's vocabulary. Alignment
        # would be meaningless, so it is reported as unreliable rather than
        # produced and quietly trusted.
        return Alignment(phones=[], aligner="ctc-wav2vec2", score=0.0), log_posteriors

    emission = torch.from_numpy(log_posteriors).unsqueeze(0)
    target_tensor = torch.tensor([[index for _, index in known]], dtype=torch.int32)

    try:
        indices, scores = F.forced_align(emission, target_tensor, blank=0)
    except Exception as error:  # noqa: BLE001 - alignment can genuinely fail
        log.warning("forced alignment failed (%s); marking result unreliable", error)
        return Alignment(phones=[], aligner="ctc-wav2vec2", score=0.0), log_posteriors

    aligned = _spans_from_path(
        indices[0].tolist(),
        [phone for phone, _ in known],
        [index for _, index in known],
    )

    # Mean per-frame alignment confidence. `gop.MIN_ALIGNMENT_SCORE` uses this
    # to decide whether a pronunciation score is trustworthy at all.
    confidence = float(np.exp(np.mean(scores[0].cpu().numpy())))

    return Alignment(phones=aligned, aligner="ctc-wav2vec2", score=confidence), log_posteriors


def _spans_from_path(
    path: list[int],
    phones: list[Phone],
    token_indices: list[int],
) -> list[AlignedPhone]:
    """Collapse a frame-wise CTC path into one time span per expected phone.

    The path repeats a token across the frames it occupies and emits blanks
    between them. Walking it in order — rather than searching for each token —
    is what keeps a repeated phoneme ("that that") mapped to two distinct spans
    instead of one merged one.
    """
    spans: list[AlignedPhone] = []
    position = 0
    frame = 0
    total = len(path)

    while position < len(phones) and frame < total:
        token = token_indices[position]

        while frame < total and path[frame] != token:
            frame += 1

        if frame >= total:
            break

        start = frame
        while frame < total and path[frame] == token:
            frame += 1

        spans.append(
            AlignedPhone(
                phone=phones[position],
                start_seconds=start * FRAME_SHIFT_SECONDS,
                end_seconds=frame * FRAME_SHIFT_SECONDS,
            )
        )
        position += 1

    return spans


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

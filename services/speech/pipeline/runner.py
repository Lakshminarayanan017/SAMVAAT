"""Pipeline orchestration.

Runs the stages that are actually available and records why each missing one was
skipped. A partial result with an explanation is far more useful than an error,
because most of the product still works without speech analysis: the learner can
type, tap symbols, sign or scan, and the practice loop does not care which.
"""

from __future__ import annotations

import logging

from pipeline import backends, g2p
from pipeline.gop import score_alignment
from pipeline.preprocess import preprocess
from pipeline.types import AnalysisResult

log = logging.getLogger("samvaad.speech.runner")


def capabilities() -> dict[str, bool]:
    """What this deployment can genuinely do right now.

    Probed, never assumed. `/capabilities` serves this straight to the client so
    it can tell a learner what is unavailable instead of leaving them waiting.
    """
    asr = backends.asr_status().available
    aligner = backends.aligner_status().available

    return {
        "asr": asr,
        "forced_alignment": aligner,
        # GOP needs both an aligner and phoneme targets to score against.
        "gop": aligner and g2p.is_available(),
        "prosody": False,  # M7
        "disfluency": False,  # M7 — needs the trained classifier
        "personalised_asr": False,  # M8
        "ppi": False,  # M7
    }


def analyse(
    audio_bytes: bytes,
    target_text: str,
    asr_model: str,
    phone_to_index: dict[str, int] | None = None,
) -> AnalysisResult:
    """Run everything available over one attempt."""
    skipped: dict[str, str] = {}
    versions: dict[str, str] = {}

    samples = preprocess(audio_bytes)

    # ── free pass: what did they actually say? ──────────────────────────────
    transcript = None
    if backends.asr_status().available:
        transcript = backends.transcribe(samples, asr_model)
        versions["asr"] = asr_model
    else:
        skipped["asr"] = backends.asr_status().detail

    # ── forced pass: how well did they say the intended thing? ──────────────
    if not g2p.is_available():
        skipped["gop"] = "phonemiser unavailable"
        return AnalysisResult(transcript=transcript, skipped=skipped, model_versions=versions)

    phones = g2p.phonemise(target_text)
    versions["g2p"] = "g2p_en/cmudict"

    if not backends.aligner_status().available:
        skipped["forced_alignment"] = backends.aligner_status().detail
        skipped["gop"] = "requires forced alignment"
        return AnalysisResult(transcript=transcript, skipped=skipped, model_versions=versions)

    alignment = backends.align(samples, phones)
    versions["aligner"] = alignment.aligner

    if phone_to_index is None:
        skipped["gop"] = "no phone inventory for the acoustic model"
        return AnalysisResult(
            transcript=transcript,
            alignment=alignment,
            skipped=skipped,
            model_versions=versions,
        )

    # Posteriors come from the acoustic model alongside alignment; wired in with
    # the ASR model work. The scorer itself is complete and tested.
    skipped["gop"] = "acoustic posteriors not yet exposed by the aligner"

    return AnalysisResult(
        transcript=transcript,
        alignment=alignment,
        skipped=skipped,
        model_versions=versions,
    )


__all__ = ["analyse", "capabilities", "score_alignment", "duration_of"]


def duration_of(samples) -> float:
    return len(samples) / 16_000

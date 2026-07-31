"""Pipeline orchestration.

Runs the stages that are actually available and records why each missing one was
skipped. A partial result with an explanation is far more useful than an error,
because most of the product still works without speech analysis: the learner can
type, tap symbols, sign or scan, and the practice loop does not care which.

STATELESS BY DESIGN
-------------------
This service holds no learner state. Baselines arrive with the request and leave
with the response; the API gateway persists them. That keeps the single security
boundary intact (ADR-0004), and it means the speech service can be restarted,
scaled to zero, or redeployed mid-session without anyone losing their history.
"""

from __future__ import annotations

import logging

from pipeline import backends, disfluency, g2p, measures, ppi, prosody
from pipeline.gop import score_alignment
from pipeline.measures import MeasurementInput
from pipeline.ppi import Baseline, CoachingCue, Dimension
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
    prosody_ready = prosody.is_available()
    disfluency_ready = disfluency.model_status().available

    return {
        "asr": asr,
        "forced_alignment": aligner,
        # GOP needs both an aligner and phoneme targets to score against.
        "gop": aligner and g2p.is_available(),
        "prosody": prosody_ready,
        # Needs the trained classifier artefact, not merely the code path.
        "disfluency": disfluency_ready,
        "personalised_asr": backends.adapter_status().available,
        # The index needs at least one measurable dimension. Prosody alone is
        # enough — a learner with no ASR still gets a rhythm trend, and that is
        # a real result rather than a placeholder.
        "ppi": prosody_ready or asr,
    }


def analyse(
    audio_bytes: bytes,
    target_text: str,
    asr_model: str,
    baselines: dict[Dimension, Baseline] | None = None,
    weights: dict[Dimension, float] | None = None,
    self_report_confidence: int | None = None,
    phone_to_index: dict[str, int] | None = None,
    speaker_id: str | None = None,
) -> AnalysisResult:
    """Run everything available over one attempt."""
    skipped: dict[str, str] = {}
    versions: dict[str, str] = {}
    baselines = dict(baselines or {})

    samples = preprocess(audio_bytes)

    transcript = _run_asr(samples, target_text, asr_model, speaker_id, skipped, versions)
    alignment, pronunciation = _run_pronunciation(
        samples, target_text, phone_to_index, skipped, versions
    )
    prosody_features = _run_prosody(samples, transcript, skipped, versions)
    events = _run_disfluency(samples, skipped, versions)

    # ── the only part a learner sees ─────────────────────────────────────────
    raw = measures.raw_dimensions(
        MeasurementInput(
            target_text=target_text,
            transcript=transcript,
            pronunciation=pronunciation,
            prosody=prosody_features,
            disfluency_spans=tuple(
                (event.type.value, event.start_seconds, event.end_seconds) for event in events
            ),
            self_report_confidence=self_report_confidence,
        )
    )

    if not raw:
        skipped["ppi"] = "no dimension could be measured on this attempt"
        return AnalysisResult(
            transcript=transcript,
            alignment=alignment,
            pronunciation=pronunciation,
            prosody=prosody_features,
            disfluency_events=tuple(events),
            skipped=skipped,
            model_versions=versions,
        )

    cues = measures.attach_cues(
        tuple(
            CoachingCue(
                dimension=Dimension.FLUENCY,
                strategy=event.strategy,
                message=event.cue,
                at_seconds=event.start_seconds,
            )
            for event in events
        ),
        pronunciation,
    )

    result = ppi.compute(raw, baselines, weights, cues)

    # Order matters: score against the baseline as it was, then fold the attempt
    # in. Reversing it scores the attempt partly against itself and makes real
    # improvement invisible.
    updated = ppi.update_baselines(raw, baselines)

    return AnalysisResult(
        transcript=transcript,
        alignment=alignment,
        pronunciation=pronunciation,
        prosody=prosody_features,
        disfluency_events=tuple(events),
        ppi=result,
        updated_baselines=updated,
        skipped=skipped,
        model_versions=versions,
    )


# ── stages ───────────────────────────────────────────────────────────────────


def _run_asr(samples, target_text, asr_model, speaker_id, skipped, versions):
    """The FREE pass: what did the learner actually say?

    Biased toward the expected phrase when the learner has an enrolment profile
    (M8 stage a). Biasing costs nothing, needs no GPU, and is the single largest
    accuracy win available for a closed-vocabulary drill on atypical speech.
    """
    if not backends.asr_status().available:
        skipped["asr"] = backends.asr_status().detail
        return None

    transcript = backends.transcribe(
        samples,
        asr_model,
        bias_phrases=(target_text,) if target_text else (),
        speaker_id=speaker_id,
    )
    versions["asr"] = asr_model
    return transcript


def _run_pronunciation(samples, target_text, phone_to_index, skipped, versions):
    """The FORCED pass: how well did they say the intended thing?"""
    if not g2p.is_available():
        skipped["gop"] = "phonemiser unavailable"
        return None, None

    phones = g2p.phonemise(target_text)
    versions["g2p"] = "g2p_en/cmudict"

    if not backends.aligner_status().available:
        skipped["forced_alignment"] = backends.aligner_status().detail
        skipped["gop"] = "requires forced alignment"
        return None, None

    alignment, posteriors = backends.align(samples, phones)
    versions["aligner"] = alignment.aligner

    # The inventory is a property of the acoustic model, so the caller only
    # overrides it in tests. Asking for it here keeps the two in step: an
    # inventory from one model and posteriors from another would align against
    # the wrong columns and score confident nonsense.
    inventory = phone_to_index if phone_to_index is not None else backends.phone_inventory()

    if posteriors is None or not inventory:
        skipped["gop"] = "acoustic posteriors not exposed by this aligner"
        return alignment, None

    return alignment, score_alignment(
        posteriors, alignment, inventory, frame_shift_seconds=backends.FRAME_SHIFT_SECONDS
    )


def _run_prosody(samples, transcript, skipped, versions):
    if not prosody.is_available():
        skipped["prosody"] = "librosa not installed"
        return None

    # Word count comes from what the recogniser heard, not from the target: a
    # learner who said six of the eight words spoke six words, and crediting
    # them with eight would report a speech rate they did not produce.
    word_count = len(transcript.text.split()) if transcript and transcript.text else None

    features = prosody.analyse(samples, word_count=word_count)
    versions["prosody"] = f"deterministic/{features.f0_backend}"
    return features


def _run_disfluency(samples, skipped, versions):
    status = disfluency.model_status()

    if not status.available:
        skipped["disfluency"] = status.detail
        return []

    model = disfluency.load_model()
    versions["disfluency"] = status.detail
    return model.detect(samples)


__all__ = ["analyse", "capabilities", "score_alignment", "duration_of"]


def duration_of(samples) -> float:
    return len(samples) / 16_000

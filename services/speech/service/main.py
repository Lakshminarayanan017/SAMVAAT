"""SAMVAAD speech service.

Deployed separately from the API because PyTorch, the forced aligner and the
phoneme model make this container multi-gigabyte with slow cold starts, and
because it scales as CPU-bound bursts rather than steady I/O (docs/ADR/0004).

    audio(16k) -> preprocess -> ASR -----------------> transcript + confidence
                             -> G2P(target) ---------> expected phonemes
                             -> forced alignment ----> phoneme boundaries
                             -> acoustic posteriors -> GOP per phoneme
                             -> prosody -------------> rate, pauses, F0, energy
                             -> disfluency ----------> events + coaching cues
                             -> PPI -----------------> baseline-relative scores

Two rules from the Ethics Charter constrain everything in this service:

  E1  No output may compare a learner to a non-disabled reference speaker.
      Raw GOP is an internal signal; only the PPI is ever surfaced.
  E3  Raw audio is deleted within 24h of feature extraction. This service holds
      audio only for the duration of a request and never writes it to disk.

STATELESSNESS
-------------
Baselines arrive in the request and leave in the response. The API gateway
persists them, because it is the single security boundary and the only thing
that talks to the database. That is why `/analyse` looks chattier than it needs
to: the alternative is a second service with its own copy of learner data.
"""

from __future__ import annotations

import logging
import time
from typing import Annotated, Literal

from fastapi import Body, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from samvaad_platform import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
    install_error_handlers,
    service_token_dependency,
)

from service.config import get_settings

configure_logging("samvaad-speech")
log = logging.getLogger("samvaad.speech")

#: Only the API gateway may call this service. See samvaad_platform.security.
require_service_token = service_token_dependency()

_STARTED_AT = time.monotonic()


# ── models ───────────────────────────────────────────────────────────────────


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    uptime_seconds: float


class Capabilities(BaseModel):
    """What this deployment can actually do right now.

    The API and the client read this rather than assuming. Stages come online
    one at a time as artefacts are deployed, and the client must degrade
    honestly — telling a learner "detailed feedback will arrive when you
    reconnect" is fine; silently returning nothing is not.
    """

    asr: bool = False
    forced_alignment: bool = False
    gop: bool = False
    prosody: bool = False
    disfluency: bool = False
    personalised_asr: bool = False
    ppi: bool = False


class BaselinePayload(BaseModel):
    """One dimension's rolling baseline, as the API stores it."""

    mean: float = 0.0
    variance: float = 0.0
    observations: int = 0


class AnalyseRequest(BaseModel):
    user_id: str = Field(min_length=1)
    target_text: str = Field(min_length=1, max_length=1000)
    #: base64 WAV, 16 kHz mono. The client uploads to object storage for
    #: retention purposes; this carries the bytes for the processing window only.
    audio_base64: str = Field(min_length=1)
    baselines: dict[str, BaselinePayload] = Field(default_factory=dict)
    scoring_weights: dict[str, float] = Field(default_factory=dict)
    self_report_confidence: int | None = Field(default=None, ge=1, le=5)
    #: Whether to use this learner's ASR adapter, when they have one.
    personalise: bool = True


class DimensionPayload(BaseModel):
    dimension: str
    score: int | None
    baseline_mean: float
    baseline_sigma: float
    observations: int
    #: Rule R3 — the learner can always see why a number moved.
    explanation: str


class CuePayload(BaseModel):
    strategy: str
    message: str
    at_seconds: float | None = None


class AnalyseResponse(BaseModel):
    """Everything the learner's client receives.

    Note what is not here: no raw GOP, no phoneme scores, no speech rate in
    words per minute, no disfluency count. Those are internal signals, and
    exposing them would hand a well-meaning frontend developer everything they
    need to build the comparison this product exists to refuse (Ethics E1).
    """

    transcript: str | None = None
    transcript_confidence: float | None = None
    #: True when transcription was too uncertain to score against. The client
    #: asks the learner to confirm rather than marking them wrong.
    needs_confirmation: bool = False
    dimensions: list[DimensionPayload] = Field(default_factory=list)
    composite: int | None = None
    calibrating: bool = True
    message: str = ""
    cues: list[CuePayload] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    #: Fold these back into storage. The service holds no state of its own.
    updated_baselines: dict[str, BaselinePayload] = Field(default_factory=dict)
    skipped: dict[str, str] = Field(default_factory=dict)
    model_versions: dict[str, str] = Field(default_factory=dict)


class EnrolmentRequest(BaseModel):
    user_id: str
    recorded_block_ids: list[str] = Field(default_factory=list)


class EnrolmentResponse(BaseModel):
    completed: int
    required: int
    fraction: float
    complete: bool
    message: str
    #: The next phrases to record, chosen for phonetic coverage.
    next_block_ids: list[str] = Field(default_factory=list)


class AdapterStatusResponse(BaseModel):
    user_id: str
    personalised: bool
    #: Present once an adapter has been trained and evaluated for this learner.
    wer_before: float | None = None
    wer_after: float | None = None
    relative_reduction: float | None = None
    message: str


# ── app ──────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SAMVAAD Speech Service",
        version=settings.version,
        description=(
            "ASR, forced alignment, GOP, prosody, disfluency and the "
            "Personal Progress Index. Stateless: baselines travel with the request."
        ),
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # No raw stack trace ever reaches a learner (Definition of Done), and the
    # request id is echoed so a support conversation can find the log line
    # without the learner having to describe what happened.
    install_error_handlers(app)

    @app.get("/healthz", response_model=Health, summary="Liveness probe")
    async def healthz() -> Health:
        return Health(
            service=settings.service_name,
            version=settings.version,
            uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
        )

    @app.get("/capabilities", response_model=Capabilities, summary="Which stages are live")
    async def capabilities() -> Capabilities:
        # Probed, never hard-coded: the answer depends on which optional
        # backends and trained artefacts are actually present on this
        # deployment. Flipping a flag by hand, without a passing eval run, is a
        # review failure.
        from pipeline.runner import capabilities as probe

        return Capabilities(**probe())

    @app.post(
        "/analyse",
        response_model=AnalyseResponse,
        summary="Analyse one attempt",
        dependencies=[Depends(require_service_token)],
    )
    async def analyse(request: Annotated[AnalyseRequest, Body()]) -> AnalyseResponse:
        import base64
        import binascii

        from pipeline.preprocess import AudioRejected
        from pipeline.runner import analyse as run

        try:
            audio = base64.b64decode(request.audio_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"error": "bad_audio", "message": "That recording could not be read."},
            ) from error

        try:
            result = run(
                audio,
                target_text=request.target_text,
                asr_model=settings.asr_model,
                baselines=_decode_baselines(request.baselines),
                weights=_decode_weights(request.scoring_weights),
                self_report_confidence=request.self_report_confidence,
                speaker_id=request.user_id if request.personalise else None,
            )
        except AudioRejected as rejected:
            # The learner-facing message, not the technical reason. The reason
            # goes to the log; the learner gets a sentence they can act on.
            log.info("audio rejected for %s: %s", request.user_id, rejected.reason)
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "audio_rejected", "message": rejected.learner_message},
            ) from rejected

        return _to_response(result)

    @app.post("/enrolment", response_model=EnrolmentResponse, summary="Speech enrolment progress")
    async def enrolment(request: Annotated[EnrolmentRequest, Body()]) -> EnrolmentResponse:
        """Where a learner is in enrolment, and what to record next.

        Skippable and resumable by construction: the client sends what has been
        recorded and gets back what is left. There is no server-side session to
        expire, so a learner who returns in three weeks resumes exactly where
        they stopped.
        """
        from pipeline.adapters import EnrolmentProgress, select_enrolment_phrases
        from service.content import load_blocks

        progress = EnrolmentProgress(
            user_id=request.user_id,
            completed=len(request.recorded_block_ids),
            recorded_block_ids=tuple(request.recorded_block_ids),
        )

        already = set(request.recorded_block_ids)
        candidates = [block for block in load_blocks() if block["id"] not in already]
        remaining = max(0, progress.required - progress.completed)

        return EnrolmentResponse(
            completed=progress.completed,
            required=progress.required,
            fraction=progress.fraction,
            complete=progress.is_complete,
            message=progress.message(),
            next_block_ids=[
                block["id"] for block in select_enrolment_phrases(candidates, remaining)
            ],
        )

    @app.get(
        "/adapter/{user_id}",
        response_model=AdapterStatusResponse,
        summary="Personalisation status for one learner",
    )
    async def adapter_status(user_id: str) -> AdapterStatusResponse:
        from pipeline.adapters import registry

        store = registry()
        record = store.get(user_id) if store else None

        if record is None or record.evaluation is None:
            return AdapterStatusResponse(
                user_id=user_id,
                personalised=False,
                message="We have not tuned the app to your voice yet.",
            )

        evaluation = record.evaluation
        return AdapterStatusResponse(
            user_id=user_id,
            personalised=record.deployed,
            wer_before=round(evaluation.wer_before, 4),
            wer_after=round(evaluation.wer_after, 4),
            relative_reduction=round(evaluation.relative_reduction, 4),
            message=evaluation.learner_message(),
        )

    return app


# ── translation between the wire format and the pipeline types ───────────────


def _decode_baselines(payload: dict[str, BaselinePayload]) -> dict:
    from pipeline.ppi import Baseline, Dimension

    decoded = {}
    for name, value in payload.items():
        try:
            dimension = Dimension(name)
        except ValueError:
            # An unknown dimension is a client on a newer or older contract.
            # Ignored rather than fatal: the attempt is still worth scoring on
            # the dimensions both sides agree about.
            log.warning("ignoring unknown PPI dimension '%s'", name)
            continue

        decoded[dimension] = Baseline(
            dimension=dimension,
            mean=value.mean,
            variance=value.variance,
            observations=value.observations,
        )

    return decoded


def _decode_weights(payload: dict[str, float]) -> dict | None:
    from pipeline.ppi import Dimension

    if not payload:
        return None

    weights = {}
    for name, value in payload.items():
        try:
            weights[Dimension(name)] = float(value)
        except ValueError:
            log.warning("ignoring unknown scoring weight '%s'", name)

    return weights or None


def _to_response(result) -> AnalyseResponse:
    from pipeline.ppi import PpiResult

    transcript = result.transcript
    ppi_result: PpiResult | None = result.ppi

    response = AnalyseResponse(
        transcript=transcript.text if transcript else None,
        transcript_confidence=transcript.confidence if transcript else None,
        # 0.75 is the contracts-package threshold below which the client asks
        # the learner to confirm rather than marking the answer wrong. It lives
        # in one place so the two services cannot disagree about it.
        needs_confirmation=bool(transcript and transcript.confidence < 0.75),
        skipped=result.skipped,
        model_versions=result.model_versions,
    )

    if ppi_result is None:
        response.message = (
            "We could not measure this one. Your answer still counts — "
            "the practice loop does not depend on the microphone."
        )
        return response

    response.dimensions = [
        DimensionPayload(
            dimension=score.dimension.value,
            score=score.score,
            baseline_mean=round(score.baseline_mean, 3),
            baseline_sigma=round(score.baseline_sigma, 3),
            observations=score.observations,
            explanation=score.explain(),
        )
        for score in ppi_result.dimensions
    ]
    response.composite = ppi_result.composite
    response.calibrating = ppi_result.calibrating
    response.message = ppi_result.message
    response.cues = [
        CuePayload(strategy=cue.strategy, message=cue.message, at_seconds=cue.at_seconds)
        for cue in ppi_result.cues
    ]
    response.weights = dict(ppi_result.weights)

    if result.updated_baselines:
        response.updated_baselines = {
            dimension.value: BaselinePayload(
                mean=baseline.mean,
                variance=baseline.variance,
                observations=baseline.observations,
            )
            for dimension, baseline in result.updated_baselines.items()
        }

    return response


app = create_app()

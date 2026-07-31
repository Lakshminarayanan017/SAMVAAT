"""SAMVAAD speech service.

Deployed separately from the API because PyTorch, the forced aligner and
openSMILE make this container multi-gigabyte with slow cold starts, and because
it scales as CPU-bound bursts rather than steady I/O (docs/ADR/0004).

Pipeline stages land here in module order across M5-M8:

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
      audio only for the duration of a request.
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from service.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger("samvaad.speech")

_STARTED_AT = time.monotonic()


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    uptime_seconds: float


class Capabilities(BaseModel):
    """What this deployment can actually do right now.

    The API and the client read this rather than assuming. During M5-M8 stages
    come online one at a time, and the client must degrade honestly - telling a
    learner "detailed feedback will arrive when you reconnect" is fine; silently
    returning nothing is not.
    """

    asr: bool = False
    forced_alignment: bool = False
    gop: bool = False
    prosody: bool = False
    disfluency: bool = False
    personalised_asr: bool = False
    ppi: bool = False


app = FastAPI(
    title="SAMVAAD Speech Service",
    version=get_settings().version,
    description="ASR, forced alignment, GOP, prosody, disfluency and the Personal Progress Index.",
)


@app.get("/healthz", response_model=Health, summary="Liveness probe")
async def healthz() -> Health:
    settings = get_settings()
    return Health(
        service=settings.service_name,
        version=settings.version,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
    )


@app.get("/capabilities", response_model=Capabilities, summary="Which pipeline stages are live")
async def capabilities() -> Capabilities:
    # Probed, never hard-coded: the answer depends on which optional backends
    # are actually installed on this deployment. Flipping a flag by hand,
    # without a passing eval run, is a review failure.
    from pipeline.runner import capabilities as probe

    return Capabilities(**probe())

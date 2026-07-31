"""Health and readiness endpoints.

`/healthz` is a liveness probe: the process is up. It must never depend on a
downstream service, or a database blip will take the whole deployment down.

`/readyz` is a readiness probe: the process can actually serve traffic. It does
check dependencies, and reports each one separately so an incident tells you
which thing broke rather than only that something did.
"""

from __future__ import annotations

import time
from typing import Literal

import httpx
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter(tags=["health"])

_STARTED_AT = time.monotonic()


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str
    uptime_seconds: float


class DependencyStatus(BaseModel):
    name: str
    healthy: bool
    detail: str | None = None


class Readiness(BaseModel):
    ready: bool
    dependencies: list[DependencyStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@router.get("/healthz", response_model=Health, summary="Liveness probe")
async def healthz() -> Health:
    settings = get_settings()
    return Health(
        service=settings.service_name,
        version=settings.version,
        environment=settings.environment,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
    )


@router.get("/readyz", response_model=Readiness, summary="Readiness probe")
async def readyz(response: Response) -> Readiness:
    settings = get_settings()
    dependencies: list[DependencyStatus] = []

    # Speech service. Degraded rather than fatal: drills, role-play and every
    # non-speech modality keep working without it, which is the whole point of
    # normalising every input mode to canonical_text (ADR-0002).
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.speech_service_url}/healthz")
        dependencies.append(
            DependencyStatus(name="speech", healthy=r.status_code == 200)
        )
    except Exception as exc:  # noqa: BLE001 - any failure is simply "not reachable"
        dependencies.append(
            DependencyStatus(name="speech", healthy=False, detail=type(exc).__name__)
        )

    warnings = settings.check_production()
    ready = all(d.healthy for d in dependencies) and not warnings

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return Readiness(ready=ready, dependencies=dependencies, warnings=warnings)

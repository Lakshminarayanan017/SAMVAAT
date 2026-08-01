"""SAMVAAD API gateway.

The single security boundary: nothing else talks to the database. Hosts the
learning service (spaced repetition, recommendation, gamification) as an internal
module rather than a separate deployment - see docs/ADR/0004.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    audio,
    auth,
    content,
    conversation,
    export,
    flags,
    health,
    institution,
    journey,
    missions,
    practice,
    profile,
    progress,
    trainer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger("samvaad.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    log.info("starting %s v%s (%s)", settings.service_name, settings.version, settings.environment)

    # Fail loudly at startup rather than quietly at runtime.
    for problem in settings.check_production():
        log.error("production configuration problem: %s", problem)

    # Importing the contracts here surfaces a missing `npm run contracts:build`
    # as a startup error with a clear message, instead of an ImportError buried
    # in the first request that happens to touch a model.
    from app import contracts  # noqa: F401

    log.info("contracts loaded")

    # Apply SAMVAAD_FLAG_<NAME>=on|off|<0-100> overrides. Without this call the
    # flag registry's defaults are the only thing anyone ever gets, and there is
    # no way — short of editing code — to turn a phase on for a deploy.
    from samvaad_platform.flags import load_from_env

    load_from_env()

    # Development and tests only. Production schema changes go through Alembic,
    # because `create_all` cannot alter an existing table and silently does
    # nothing when a column has been added — which looks exactly like success.
    from app.db.session import create_all, dispose
    from app.models import tables  # noqa: F401  (registers the mappings)

    if settings.database_url.startswith("sqlite"):
        await create_all()
        log.info("schema ensured (sqlite)")

    yield

    await dispose()
    log.info("shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SAMVAAD API",
        version=settings.version,
        description=(
            "Ability-adaptive workplace communication training. "
            "See docs/EXECUTION_PLAN.md for the module map."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(content.router)
    app.include_router(practice.router)
    app.include_router(audio.router)
    app.include_router(conversation.router)
    app.include_router(profile.router)
    app.include_router(journey.router)
    app.include_router(progress.router)
    app.include_router(trainer.router)
    app.include_router(institution.router)
    app.include_router(export.router)
    app.include_router(flags.router)
    app.include_router(missions.router)

    return app


app = create_app()

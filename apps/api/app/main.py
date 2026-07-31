"""SAMVAAD API gateway.

The single security boundary: nothing else talks to the database. Hosts the
learning service (spaced repetition, recommendation, gamification) as an internal
module rather than a separate deployment - see docs/ADR/0004.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger("samvaad.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
    yield
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

    return app


app = create_app()

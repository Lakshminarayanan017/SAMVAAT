"""Application settings, loaded from the environment.

Every setting has a development default so a fresh clone boots with no .env at
all. Anything that must differ in production is validated in `check_production`
rather than being silently wrong.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── identity ──────────────────────────────────────────────────────────────
    service_name: str = "samvaad-api"
    environment: Literal["development", "staging", "production"] = "development"
    version: str = "0.1.0"

    # ── network ───────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="The web client's dev server. Production origins are set per deployment.",
    )

    # ── downstream services ───────────────────────────────────────────────────
    speech_service_url: str = "http://localhost:8100"
    genai_service_url: str = "http://localhost:8200"
    database_url: str = "postgresql+asyncpg://samvaad:samvaad@localhost:5432/samvaad"

    #: Shared secret proving a caller is one of our own services. The speech and
    #: GenAI services run on hosts with public URLs; without this, anyone who
    #: finds the URL can spend our CPU and our LLM budget.
    #:
    #: Unset in development so a fresh clone runs with no configuration at all.
    #: That is safe only because the downstream services fail closed in
    #: production — see packages/platform/samvaad_platform/security.py.
    service_token: str = ""

    # ── privacy (Ethics E3) ───────────────────────────────────────────────────
    audio_retention_hours: int = Field(
        default=24,
        le=24,
        description=(
            "Hard ceiling on raw audio retention after feature extraction. Ethics rule E3 "
            "sets 24h; the `le` constraint means a longer value fails at startup rather "
            "than quietly weakening the guarantee."
        ),
    )

    def check_production(self) -> list[str]:
        """Settings that are acceptable in development but not in production."""
        problems: list[str] = []
        if self.environment != "production":
            return problems
        if "localhost" in self.database_url:
            problems.append("database_url still points at localhost")
        if any("localhost" in o for o in self.cors_origins):
            problems.append("cors_origins still contains a localhost origin")
        if "localhost" in self.speech_service_url:
            problems.append("speech_service_url still points at localhost")
        if "localhost" in self.genai_service_url:
            problems.append("genai_service_url still points at localhost")
        if not self.service_token:
            # Without it, our speech and GenAI hosts are open compute endpoints
            # with our name on the bill.
            problems.append("service_token is not set; downstream services are unauthenticated")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()

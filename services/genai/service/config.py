"""GenAI service settings.

Every setting has a development default, so a fresh clone boots with no .env at
all and no API key. Anything that must differ in production is validated in
`check_production` rather than being silently wrong.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "samvaad-genai"
    environment: Literal["development", "staging", "production"] = "development"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8200

    # ── the model ────────────────────────────────────────────────────────────
    anthropic_api_key: str | None = Field(
        default=None,
        description="Optional. Without it the service runs on authored content: every "
        "feature works, nothing is generated, and /capabilities says so.",
    )
    llm_model: str = "claude-sonnet-4-5"
    llm_cheap_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Classification and routing sub-calls. Using a frontier model to "
        "decide whether an utterance is on-topic is the easiest way to spend the "
        "budget on nothing.",
    )
    llm_timeout_seconds: float = 20.0

    # ── cost control ─────────────────────────────────────────────────────────
    daily_user_token_budget: int = Field(
        default=40_000,
        description="Per learner per day. At the limit, generation stops and authored "
        "content takes over — the learner is never locked out.",
    )
    daily_global_token_budget: int = Field(
        default=1_500_000,
        description="Across all learners. The wall a fan-out bug hits.",
    )
    cache_capacity: int = 2_000

    # ── rubric ───────────────────────────────────────────────────────────────
    rubric_version: str = Field(
        default="rubric-v1",
        description="Persisted with every score. An audit two years later must be able "
        "to say which rubric produced a number.",
    )
    rubric_self_consistency_runs: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Score N times and take the median. LLM scoring variance is the "
        "known weakness of this approach, and the median of three is the cheapest "
        "meaningful mitigation.",
    )

    def check_production(self) -> list[str]:
        """Settings acceptable in development but not in production."""
        problems: list[str] = []

        if self.environment != "production":
            return problems

        if not self.anthropic_api_key:
            # Not fatal. A production deployment serving authored content is a
            # degraded product, not a broken one — but nobody should discover
            # that from a learner's complaint.
            problems.append(
                "no LLM provider configured; role-play and interviews will serve "
                "authored content only"
            )

        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Speech service settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "samvaad-speech"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8100

    # ── audio ────────────────────────────────────────────────────────────────
    sample_rate: int = Field(
        default=16_000,
        description="All audio is resampled client-side to this. Inconsistent input silently "
        "destroys every downstream metric, so the rate is fixed, not negotiated.",
    )
    max_utterance_seconds: int = Field(
        default=120,
        description="A safety ceiling on processing cost, NOT a recording limit. "
        "Ethics E6: recording itself is never time-limited.",
    )

    # ── models (populated as M6-M8 land) ─────────────────────────────────────
    asr_model: str = "openai/whisper-small"
    asr_model_local: str = "onnx/whisper-base-int8"

    @property
    def model_versions(self) -> dict[str, str]:
        """Recorded on every attempt so scores stay interpretable after an upgrade."""
        return {"asr": self.asr_model}


@lru_cache
def get_settings() -> Settings:
    return Settings()

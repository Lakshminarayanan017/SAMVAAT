"""Speech service settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Repository-relative default for trained artefacts. Weights are NOT in version
#: control — they belong in the model registry (see training/README.md), and a
#: 40 MB binary in git is a permanent tax on every clone.
_DEFAULT_ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"


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

    # ── models ───────────────────────────────────────────────────────────────
    asr_model: str = "openai/whisper-small"
    asr_model_local: str = "onnx/whisper-base-int8"

    artifacts_dir: Path = Field(
        default=_DEFAULT_ARTIFACTS,
        description="Where trained artefacts are mounted. Populated by the deploy step "
        "that pulls from the model registry; empty on a fresh clone, and every "
        "stage that needs one reports itself unavailable rather than guessing.",
    )

    disfluency_threshold: float = Field(
        default=0.5,
        ge=0.05,
        le=0.95,
        description="Fallback probability above which an event is reported. The real "
        "thresholds are per event type and are read from artifacts/metrics.json, "
        "tuned on the validation split for balanced recall — one global threshold "
        "across five imbalanced classes silences the rare ones, and the rarest here "
        "is `block`, the event P5 most needs recognised.",
    )

    adapters_dir: Path | None = Field(
        default=None,
        description="Per-learner ASR adapters (M8). Each is 2-5 MB and is loaded on "
        "demand. None disables personalisation; base ASR still runs.",
    )

    # ── model registry ───────────────────────────────────────────────────────
    model_registry_uri: str | None = Field(
        default=None,
        description="MLflow tracking URI. Every artefact this service loads was "
        "registered there with its eval table; see docs/MLOPS.md.",
    )

    @property
    def model_versions(self) -> dict[str, str]:
        """Recorded on every attempt so scores stay interpretable after an upgrade.

        Asking the pipeline rather than reading a config value: the version that
        matters is the one actually loaded, and a config string can drift from
        the file on disk without anything noticing.
        """
        from pipeline.disfluency import model_status

        versions = {"asr": self.asr_model}

        status = model_status()
        if status.available:
            versions["disfluency"] = status.detail

        return versions


@lru_cache
def get_settings() -> Settings:
    return Settings()

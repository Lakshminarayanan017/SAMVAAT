"""Shared test scaffolding for the speech service.

The service is built so that every heavy dependency is optional and probed
rather than assumed — that is what lets it boot on a free-tier host and report
honestly through `/capabilities`. The tests have to hold the same shape: a
minimal install must produce *skips with reasons*, not errors.

The distinction that matters:

  * Tests of the ETHICS properties — coaching cues never becoming deductions,
    the PPI never referencing a non-disabled speaker, timing never reaching the
    scheduler — never skip. They depend on nothing optional, deliberately, and a
    skipped fairness test is indistinguishable from a passing one in a CI log.

  * Tests of the SIGNAL PROCESSING skip only when the audio tier is genuinely
    absent. CI installs that tier, so in CI they run.
"""

from __future__ import annotations

import importlib.util

import pytest


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):  # pragma: no cover - malformed install
        return False


HAS_LIBROSA = _installed("librosa")
HAS_PARSELMOUTH = _installed("parselmouth")
HAS_TORCH = _installed("torch")


def _g2p_ready() -> bool:
    from pipeline import g2p

    return g2p.is_available()


HAS_G2P = _g2p_ready()


requires_librosa = pytest.mark.skipif(
    not HAS_LIBROSA,
    reason="librosa not installed — pip install -r requirements.txt",
)

requires_parselmouth = pytest.mark.skipif(
    not HAS_PARSELMOUTH,
    reason="praat-parselmouth not installed — pip install -r requirements.txt",
)

requires_g2p = pytest.mark.skipif(
    not HAS_G2P,
    reason="phonemisation unavailable — run `python -m scripts.warm_g2p`",
)

requires_torch = pytest.mark.skipif(
    not HAS_TORCH,
    reason="torch not installed — pip install -r requirements-ml.txt",
)

"""Speech service smoke tests and evaluation-discipline guards."""

from __future__ import annotations

from fastapi.testclient import TestClient

from eval.harness import TARGETS, run
from service.main import app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["service"] == "samvaad-speech"


def test_capabilities_are_honest() -> None:
    """Capabilities must report what is actually implemented.

    The client uses this to degrade honestly. A flag flipped true without a
    passing eval run is how a learner ends up staring at a spinner that will
    never resolve.
    """
    with TestClient(app) as client:
        capabilities = client.get("/capabilities").json()

    assert set(capabilities) == {
        "asr",
        "forced_alignment",
        "gop",
        "prosody",
        "disfluency",
        "personalised_asr",
        "ppi",
    }
    # No pipeline stage has landed yet; every flag must still be false.
    assert not any(capabilities.values())


def test_eval_harness_runs_before_any_model_exists() -> None:
    """The harness must be usable from day one, not once there is something to measure."""
    report = run("atypical")
    rendered = report.render()

    assert "Speech eval" in rendered
    assert "No results" in rendered
    # It must still advertise the bars it will enforce.
    for target in TARGETS:
        assert target.metric in rendered


def test_fairness_targets_are_registered() -> None:
    """The two fairness gates are not optional and must never be quietly dropped."""
    metrics = {t.metric for t in TARGETS}
    assert "ppi_monotonicity" in metrics
    assert "ppi_disfluency_invariance" in metrics

"""Speech service smoke tests and evaluation-discipline guards."""

from __future__ import annotations

from fastapi.testclient import TestClient

from eval.harness import TARGETS, run, run_gates
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

    # Prosody is deterministic signal processing and needs no weights, so it is
    # true on any correctly installed host. Everything requiring torch or a
    # trained artefact must be false here — this environment has neither.
    assert capabilities["prosody"] is True
    assert capabilities["ppi"] is True
    assert capabilities["disfluency"] is False


def test_disfluency_is_never_claimed_without_the_trained_classifier() -> None:
    """The one capability that cannot be produced by writing code.

    SEP-28k training is the outstanding manual step (docs/TRAINING_HANDOFF.md).
    Until an artefact exists, this flag stays false and the client tells the
    learner fluency coaching is unavailable — rather than showing them invented
    cues about speech they did not produce.
    """
    from pipeline.disfluency import model_status

    status = model_status()
    if not status.available:
        with TestClient(app) as client:
            assert client.get("/capabilities").json()["disfluency"] is False


def test_analyse_requires_readable_audio() -> None:
    """A bad upload gets a learner-facing sentence, never a stack trace."""
    with TestClient(app) as client:
        response = client.post(
            "/analyse",
            json={
                "user_id": "p3-arjun",
                "target_text": "Could you please repeat that?",
                "audio_base64": "not base64 at all!!",
            },
        )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "bad_audio"
    # Dignity rules apply to error copy too: no jargon, no blame.
    assert "recording" in body["message"].lower()
    assert not any(word in body["message"].lower() for word in ("invalid", "base64", "error"))


def test_eval_harness_runs_before_any_corpus_exists() -> None:
    """The harness must be usable from day one, not once there is something to measure."""
    report = run("atypical")
    rendered = report.render()

    assert "Speech eval" in rendered
    assert "no licensed corpus" in rendered
    # It must still advertise the bars it will enforce.
    for target in TARGETS:
        assert target.metric in rendered


def test_fairness_targets_are_registered() -> None:
    """The two fairness gates are not optional and must never be quietly dropped."""
    metrics = {t.metric for t in TARGETS}
    assert "ppi_monotonicity" in metrics
    assert "ppi_disfluency_invariance" in metrics


def test_fairness_gates_run_without_any_dataset() -> None:
    """They are properties of our own scoring maths, not of a corpus.

    That is what makes them enforceable in CI today rather than deferred until
    UASpeech access comes through — and deferred fairness checks are how a
    project ends up discovering the problem in week 14.
    """
    results = run_gates()

    assert {gate.name for gate in results} == {
        "ppi_monotonicity",
        "ppi_disfluency_invariance",
    }
    for gate in results:
        assert gate.passed, f"{gate.name} failed: {gate.detail}"
        assert gate.detail, "a gate must explain its own result"

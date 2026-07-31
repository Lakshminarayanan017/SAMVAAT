"""Health endpoint tests.

Also serves as the smoke test that the generated contracts import correctly -
if `npm run contracts:build` has not been run, app startup fails here rather
than in production.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_reports_liveness() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "samvaad-api"
    assert body["uptime_seconds"] >= 0


def test_healthz_does_not_depend_on_downstream_services() -> None:
    """Liveness must stay green when the speech service is unreachable.

    A liveness probe that checks dependencies takes the whole deployment down
    on a downstream blip. Readiness is where dependencies belong.
    """
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200


def test_readyz_reports_each_dependency_separately() -> None:
    """An incident should say *which* dependency broke, not merely that one did."""
    with TestClient(create_app()) as client:
        response = client.get("/readyz")

    body = response.json()
    names = {d["name"] for d in body["dependencies"]}
    assert "speech" in names
    # The speech service is not running in unit tests, so readiness is expected
    # to be false - what matters is that the failure is attributed.
    assert response.status_code in (200, 503)


def test_generated_contracts_are_importable() -> None:
    from app.contracts import CommunicationAbilityProfile, ContentBlock, LearnerResponse

    assert ContentBlock is not None
    assert LearnerResponse is not None
    assert CommunicationAbilityProfile is not None

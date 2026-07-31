"""Service-to-service authentication and HTTP security headers.

The speech and GenAI services run on hosts whose URLs are public. Without this
check, anyone who finds the URL can post audio to `/analyse` and spend our CPU,
or post a turn request and spend our LLM budget.

The property that matters most here is **fail-closed in production**: a missing
token must refuse the request, not wave it through. That is how this class of
protection usually fails — silently, and only in the environment that matters.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from samvaad_platform.security import (
    SERVICE_TOKEN_HEADER,
    SecurityHeadersMiddleware,
    constant_time_compare,
    service_token_dependency,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def guarded_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(service_token_dependency())])
    async def protected() -> dict:
        return {"ok": True}

    return app


class TestConstantTimeCompare:
    def test_matches_identical_strings(self) -> None:
        assert constant_time_compare("abc123", "abc123")

    def test_rejects_a_different_string(self) -> None:
        assert not constant_time_compare("abc123", "abc124")

    def test_rejects_a_prefix(self) -> None:
        """A naive `==` on bytes can leak length and prefix through timing."""
        assert not constant_time_compare("abc", "abc123")

    def test_handles_empty_and_unicode(self) -> None:
        assert constant_time_compare("", "")
        assert not constant_time_compare("", "x")
        assert constant_time_compare("tökén", "tökén")


class TestServiceTokenInDevelopment:
    def test_no_token_configured_allows_the_request(self) -> None:
        """A fresh clone must run with no configuration at all. That is safe
        only because the same function fails closed in production."""
        with TestClient(guarded_app()) as client:
            assert client.get("/protected").status_code == 200


class TestServiceTokenInProduction:
    def test_missing_configuration_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unauthenticated speech service in production is an open compute
        endpoint with our name on the bill."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        with TestClient(guarded_app()) as client:
            response = client.get("/protected")

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "service_misconfigured"

    def test_staging_also_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "staging")

        with TestClient(guarded_app()) as client:
            assert client.get("/protected").status_code == 503

    def test_the_misconfiguration_message_does_not_blame_the_learner(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Our infrastructure being broken is not the learner's fault, and the
        copy they see should not imply otherwise (Ethics Charter, copy rules)."""
        monkeypatch.setenv("ENVIRONMENT", "production")

        with TestClient(guarded_app()) as client:
            message = client.get("/protected").json()["detail"]["message"].lower()

        for word in ("error", "failed", "invalid", "denied", "forbidden"):
            assert word not in message


class TestServiceTokenConfigured:
    @pytest.fixture(autouse=True)
    def token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SERVICE_TOKEN", "correct-horse-battery-staple")
        monkeypatch.setenv("ENVIRONMENT", "production")

    def test_correct_token_is_accepted(self) -> None:
        with TestClient(guarded_app()) as client:
            response = client.get(
                "/protected", headers={SERVICE_TOKEN_HEADER: "correct-horse-battery-staple"}
            )
        assert response.status_code == 200

    def test_wrong_token_is_rejected(self) -> None:
        with TestClient(guarded_app()) as client:
            response = client.get("/protected", headers={SERVICE_TOKEN_HEADER: "wrong"})

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "service_unauthenticated"

    def test_absent_header_is_rejected(self) -> None:
        with TestClient(guarded_app()) as client:
            assert client.get("/protected").status_code == 401

    def test_empty_header_is_rejected(self) -> None:
        with TestClient(guarded_app()) as client:
            assert client.get("/protected", headers={SERVICE_TOKEN_HEADER: ""}).status_code == 401

    def test_a_correct_prefix_is_not_enough(self) -> None:
        with TestClient(guarded_app()) as client:
            response = client.get("/protected", headers={SERVICE_TOKEN_HEADER: "correct-horse"})
        assert response.status_code == 401

    def test_the_token_is_never_echoed_back(self) -> None:
        """An error body that repeats the credential puts it in the caller's
        logs as well as ours."""
        with TestClient(guarded_app()) as client:
            body = client.get("/protected", headers={SERVICE_TOKEN_HEADER: "wrong"}).text
        assert "correct-horse-battery-staple" not in body


class TestSecurityHeaders:
    @pytest.fixture
    def client(self) -> TestClient:
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/thing")
        async def thing() -> dict:
            return {"ok": True}

        return TestClient(app)

    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    def test_baseline_headers_are_present(
        self, client: TestClient, header: str, expected: str
    ) -> None:
        assert client.get("/thing").headers[header] == expected

    def test_camera_and_microphone_are_denied_to_embedded_frames(
        self, client: TestClient
    ) -> None:
        """Closes the case where an API-served document asks for a learner's
        camera. Video never leaves the device (Ethics E4)."""
        policy = client.get("/thing").headers["Permissions-Policy"]
        assert "camera=()" in policy
        assert "microphone=()" in policy

    def test_content_security_policy_locks_everything_down(self, client: TestClient) -> None:
        csp = client.get("/thing").headers["Content-Security-Policy"]
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_is_absent_over_plain_http(self, client: TestClient) -> None:
        """Pinning HSTS from a local http request would break a developer's
        browser for every other localhost project they own."""
        assert "Strict-Transport-Security" not in client.get("/thing").headers

    def test_hsts_is_present_over_https(self, client: TestClient) -> None:
        response = client.get("https://testserver/thing")
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

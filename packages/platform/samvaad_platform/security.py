"""Service-to-service authentication and HTTP security headers.

THE THREAT THIS CLOSES
----------------------
The speech service and the GenAI service run on hosts whose URLs are public
(Hugging Face Spaces, Render). Without a check, anyone who finds the URL can
post audio to `/analyse` and spend our CPU, or post a turn request and spend our
LLM budget. Neither service should ever be reachable by anything except the API
gateway.

A shared token is the right weight for this. It is not user authentication —
that is the API gateway's job and it uses JWTs — it is a statement that the
caller is one of our own services. Rotating it is a config change on two hosts.
"""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("samvaad.security")

SERVICE_TOKEN_HEADER = "X-Service-Token"


def constant_time_compare(left: str, right: str) -> bool:
    """Compare without leaking length or prefix through timing."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def service_token_dependency(
    env_var: str = "SERVICE_TOKEN",
    *,
    required_in: tuple[str, ...] = ("production", "staging"),
):
    """Build a FastAPI dependency that checks the shared service token.

    Unset in development so a fresh clone runs with no configuration at all —
    that is a deliberate developer-experience choice, and it is safe only
    because the same function refuses to start without the token in production.
    A silent "no token configured, allow everything" in production is how this
    class of protection actually fails.
    """

    async def check(
        token: str | None = Header(default=None, alias=SERVICE_TOKEN_HEADER),
    ) -> None:
        expected = os.getenv(env_var)
        environment = os.getenv("ENVIRONMENT", "development")

        if not expected:
            if environment in required_in:
                # Fail closed. An unauthenticated speech service in production
                # is an open compute endpoint with our name on the bill.
                log.error("%s is not set in %s; refusing the request", env_var, environment)
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "service_misconfigured",
                        "message": "That part of the app is resting. Everything else still works.",
                    },
                )
            return

        if not token or not constant_time_compare(token, expected):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "service_unauthenticated",
                    "message": "Please sign in again to continue.",
                },
            )

    return check


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """The headers every response carries.

    A JSON API does not render HTML, so several of these are belt-and-braces —
    but a JSON API that one day serves an error page, a docs page, or a PDF
    export does render HTML, and the day it starts is not the day anyone
    remembers to add a CSP.
    """

    def __init__(self, app, *, connect_src: tuple[str, ...] = ()) -> None:
        super().__init__(app)
        self.connect_src = connect_src

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            # Camera and microphone are used only by the client, never by an
            # embedded frame of ours. Denying them here costs nothing and closes
            # the case where an API-served document asks for a learner's camera.
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )

        # HSTS only when the request actually arrived over TLS, so local
        # development over http is not permanently pinned in a developer's
        # browser.
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response

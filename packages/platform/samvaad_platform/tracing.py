"""Request correlation across three services.

A learner presses record. The client calls the API, the API calls the speech
service, the speech service answers, the API calls the GenAI service for the
coaching copy. When that fails, four log streams have to be joinable — otherwise
diagnosing anything means guessing at timestamps.

One header, `X-Request-Id`, generated at the edge if absent and propagated
everywhere. Stored in a `ContextVar` so it reaches the logging formatter without
being threaded through every function signature.
"""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-Id"

_request_id: ContextVar[str | None] = ContextVar("samvaad_request_id", default=None)


def request_id() -> str | None:
    """The current request's id, or None outside a request."""
    return _request_id.get()


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def new_request_id() -> str:
    return uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adopt or mint a request id, and echo it back on the response.

    Echoing matters for support: a learner or a trainer can read the id off an
    error screen, and it is the only thing they need to say for the failure to
    be findable in the logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)

        # Only adopt an id that looks like one of ours. Accepting arbitrary
        # client-supplied strings puts unvalidated input straight into every log
        # line, which is log injection with extra steps.
        identifier = incoming if _looks_like_id(incoming) else new_request_id()

        token = _request_id.set(identifier)
        request.state.request_id = identifier

        try:
            response = await call_next(request)
        finally:
            _request_id.reset(token)

        response.headers[REQUEST_ID_HEADER] = identifier
        return response


def _looks_like_id(value: str | None) -> bool:
    return bool(value) and len(value) <= 64 and all(c.isalnum() or c in "-_" for c in value)


def outbound_headers() -> dict[str, str]:
    """Headers to attach when calling another SAMVAAD service.

    Used by every `httpx` call between services. Without it the trace stops at
    the first hop, which is exactly where it stops being useful.
    """
    identifier = request_id()
    return {REQUEST_ID_HEADER: identifier} if identifier else {}

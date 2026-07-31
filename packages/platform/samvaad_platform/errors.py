"""One error shape for every service.

RFC 7807-shaped, plus two fields this product needs:

  * `message` — written for a learner, not for a developer. It appears on
    screen, it is read aloud by a screen reader, and it is rendered through the
    Modality Router like everything else. "500 Internal Server Error" is not an
    accessible error state; "Something went wrong on our side. Your recording
    was not lost." is.

  * `request_id` — so a learner or trainer can report a failure by reading one
    short string, rather than describing what they were doing.

No stack trace ever crosses this boundary. The Definition of Done says errors
are surfaced accessibly with no raw stack traces, and the way to guarantee that
is to have no code path that can emit one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from samvaad_platform.redaction import scrub
from samvaad_platform.tracing import request_id

log = logging.getLogger("samvaad.errors")


@dataclass(frozen=True)
class ProblemDetail:
    """The body every non-2xx response carries."""

    #: Machine-readable, stable, snake_case. The client branches on this.
    error: str
    #: Human-readable, learner-facing, dignified. Never mentions a stack, a
    #: table name, or a status code.
    message: str
    status: int = 500
    #: Optional structured extras — which field failed validation, which consent
    #: purpose is missing. Scrubbed before it leaves.
    details: dict = field(default_factory=dict)

    def to_response(self) -> JSONResponse:
        body = {
            "error": self.error,
            "message": self.message,
        }
        if self.details:
            body["details"] = scrub(self.details)

        identifier = request_id()
        if identifier:
            body["request_id"] = identifier

        return JSONResponse(status_code=self.status, content=body)


#: Learner-facing text per status code. Deliberately short, deliberately warm,
#: and deliberately never blaming the person on the other end.
_DEFAULT_MESSAGE: dict[int, str] = {
    400: "We could not read that request. Please try again.",
    401: "Please sign in again to continue.",
    403: "You do not have permission for that. If this seems wrong, ask your trainer.",
    404: "We could not find that.",
    409: "That has already been done.",
    413: "That file is too large for us to handle.",
    422: "Something in that did not look right. Please check and try again.",
    429: "You are going a little fast for us. Please wait a moment and try again.",
    503: "That part of the app is resting. Everything else still works.",
}

_FALLBACK = "Something went wrong on our side. Nothing you did caused this."


def install_error_handlers(app: FastAPI) -> None:
    """Attach the handlers. Called by every service's `create_app`."""

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        # A handler that raised `HTTPException(403, detail={...})` has already
        # written a learner-facing message; respect it rather than overwriting.
        if isinstance(error.detail, dict) and "message" in error.detail:
            detail = dict(error.detail)
            return ProblemDetail(
                error=str(detail.pop("error", "request_failed")),
                message=str(detail.pop("message")),
                status=error.status_code,
                details=detail,
            ).to_response()

        return ProblemDetail(
            error=_slug(error.status_code),
            message=_DEFAULT_MESSAGE.get(error.status_code, _FALLBACK),
            status=error.status_code,
        ).to_response()

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        # The field names, never the values. A rejected value is very often the
        # learner's own words, and echoing it back into an error payload sends
        # it to every log and monitor the response passes through.
        fields = sorted({".".join(str(part) for part in e["loc"][1:]) for e in error.errors()})

        return ProblemDetail(
            error="validation_failed",
            message=_DEFAULT_MESSAGE[422],
            status=422,
            details={"fields": fields},
        ).to_response()

    @app.exception_handler(Exception)
    async def unhandled(request: Request, error: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return ProblemDetail(error="internal_error", message=_FALLBACK, status=500).to_response()


def _slug(status: int) -> str:
    return {
        400: "bad_request",
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_failed",
        429: "rate_limited",
        503: "unavailable",
    }.get(status, "request_failed")

"""Structured logging.

JSON in production because that is what a log aggregator can query; human-
readable in development because that is what a person can read. One switch,
driven by the environment, and never both.

Every record carries the request id, so a failure spanning three services can be
reconstructed from a single search. Every record passes through the redaction
formatter, so learner content cannot reach the log even if a call site passes it
— which is the whole point of doing this at the formatter and not at the call
site.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

from samvaad_platform.redaction import scrub, scrub_text
from samvaad_platform.tracing import request_id

#: Standard LogRecord attributes, so `extra=` fields can be found by difference.
_RESERVED = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "module", "msecs",
        "message", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    }
)


class RedactingJsonFormatter(logging.Formatter):
    """One JSON object per line, with learner content removed."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "message": scrub_text(record.getMessage()),
        }

        identifier = request_id()
        if identifier:
            payload["request_id"] = identifier

        extras = {
            key: value for key, value in record.__dict__.items() if key not in _RESERVED
        }
        if extras:
            payload.update(scrub(extras))

        if record.exc_info:
            # The type and the message, never the full traceback: tracebacks
            # routinely contain argument values, and argument values here are
            # learner speech.
            exc_type, exc_value, _ = record.exc_info
            payload["error_type"] = getattr(exc_type, "__name__", str(exc_type))
            payload["error_message"] = scrub_text(str(exc_value))

        return json.dumps(payload, default=str)


class RedactingTextFormatter(logging.Formatter):
    """Development output. Redacted too — a developer's terminal is still a
    place learner speech should not end up, and habits formed locally are the
    habits that ship."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s  %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        identifier = request_id()
        rendered = super().format(record)
        if identifier:
            rendered = f"{rendered}  [{identifier[:8]}]"
        return scrub_text(rendered)


def configure_logging(service: str, level: str | None = None) -> None:
    """Install the formatter for one service. Idempotent.

    Called once at import time by each service's `main`. Re-running it replaces
    the handler rather than stacking a second one, so a test that imports two
    apps does not get every line twice.
    """
    environment = os.getenv("ENVIRONMENT", "development")
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingJsonFormatter(service)
        if environment in {"production", "staging"}
        else RedactingTextFormatter()
    )
    handler.set_name("samvaad")

    root = logging.getLogger()
    for existing in [h for h in root.handlers if h.get_name() == "samvaad"]:
        root.removeHandler(existing)

    root.addHandler(handler)
    root.setLevel(resolved)

    # These libraries log every request at INFO, including full URLs. URLs in
    # this system carry user ids and object keys, so they are turned down rather
    # than relied upon.
    for noisy in ("httpx", "httpcore", "urllib3", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

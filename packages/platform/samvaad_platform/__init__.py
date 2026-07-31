"""Cross-service platform primitives.

Shared rather than copied because each of these is a rule that only works if all
three services obey the same version of it. See README.md.
"""

from samvaad_platform.errors import ProblemDetail, install_error_handlers
from samvaad_platform.logging import configure_logging
from samvaad_platform.ratelimit import RateLimit, RateLimiter, TokenBucket
from samvaad_platform.redaction import SENSITIVE_KEYS, scrub
from samvaad_platform.security import (
    SecurityHeadersMiddleware,
    constant_time_compare,
    service_token_dependency,
)
from samvaad_platform.tracing import RequestContextMiddleware, request_id, set_request_id

__all__ = [
    "ProblemDetail",
    "RateLimit",
    "RateLimiter",
    "RequestContextMiddleware",
    "SENSITIVE_KEYS",
    "SecurityHeadersMiddleware",
    "TokenBucket",
    "configure_logging",
    "constant_time_compare",
    "install_error_handlers",
    "request_id",
    "scrub",
    "service_token_dependency",
    "set_request_id",
]

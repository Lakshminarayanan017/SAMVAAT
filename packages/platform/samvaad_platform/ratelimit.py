"""Rate limiting.

A token bucket rather than a fixed window: a fixed window lets a client fire the
whole quota in the last millisecond of one window and again in the first of the
next, which is the burst you were trying to prevent, doubled.

THE ACCESSIBILITY CONSTRAINT ON RATE LIMITING
---------------------------------------------
Limits here are generous and are set per *expensive operation*, never per
interaction. A learner using switch scanning generates many more UI events than
someone using a mouse; a learner with a tremor may tap the same control several
times. Neither is abuse, and a limiter tuned on typical interaction rates would
throttle exactly the people this product exists for.

So: no limit on reading content, no limit on submitting a practice answer, and
real limits only on the things that cost money or compute — speech analysis, LLM
turns, exports, and authentication attempts.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimit:
    """A budget, and the window it refills over."""

    #: Operations allowed in a full bucket. Also the maximum burst.
    capacity: int
    #: Seconds for an empty bucket to refill completely.
    refill_seconds: float
    #: Shown to the caller when the limit is hit. Learner-facing.
    message: str = "You are going a little fast for us. Please wait a moment and try again."

    @property
    def refill_rate(self) -> float:
        return self.capacity / self.refill_seconds


#: The named limits this product uses. Named rather than inline so they are
#: reviewable in one place and so a limit cannot be tightened by accident in a
#: pull request about something else.
LIMITS: dict[str, RateLimit] = {
    # Speech analysis costs real CPU on a free host. 30 per 5 minutes is far
    # more than a practice session needs and far less than a scraper wants.
    "speech_analyse": RateLimit(capacity=30, refill_seconds=300),
    # LLM turns cost money. Also enforced per-day by the token budget in the
    # GenAI service; this is the burst guard, that is the spend guard.
    "llm_turn": RateLimit(capacity=20, refill_seconds=120),
    # Auth attempts. Tight, because this one is an attack surface.
    "auth": RateLimit(
        capacity=8,
        refill_seconds=300,
        message="Too many sign-in attempts. Please wait five minutes and try again.",
    ),
    # Data export builds a PDF and reads every table the learner owns.
    "export": RateLimit(capacity=5, refill_seconds=3600),
    # Adapter training is the most expensive thing a single user can trigger.
    "adapter_training": RateLimit(capacity=3, refill_seconds=86_400),
}


class RateLimiter(Protocol):
    """The seam a Redis implementation fills for multi-instance deploys."""

    def check(self, key: str, limit: RateLimit) -> tuple[bool, float]: ...


class TokenBucket:
    """In-process token bucket.

    Correct for a single instance, which is what the free tier runs. It is
    deliberately not silently wrong on multiple instances: `is_distributed` is
    False, and the readiness probe surfaces that so nobody discovers it during
    an incident. The Redis-backed implementation lands with horizontal scaling.
    """

    is_distributed = False

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()
        self._last_swept = time.monotonic()

    def check(self, key: str, limit: RateLimit) -> tuple[bool, float]:
        """Consume one token.

        Returns `(allowed, retry_after_seconds)`. `retry_after` is 0 when
        allowed, and is a real number of seconds otherwise — clients render it
        as "try again in a moment", never as a countdown timer (Ethics E6).
        """
        now = time.monotonic()

        with self._lock:
            self._sweep(now)

            tokens, last_seen = self._buckets.get(key, (float(limit.capacity), now))
            tokens = min(limit.capacity, tokens + (now - last_seen) * limit.refill_rate)

            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False, (1.0 - tokens) / limit.refill_rate

            self._buckets[key] = (tokens - 1.0, now)
            return True, 0.0

    def _sweep(self, now: float, interval: float = 300.0) -> None:
        """Drop buckets that have refilled completely.

        Without this the dictionary grows one entry per user forever, which on a
        512 MB free-tier host is a slow memory leak that presents as an
        unexplained restart three weeks after launch.
        """
        if now - self._last_swept < interval:
            return

        self._buckets = {
            key: value for key, value in self._buckets.items() if now - value[1] < interval
        }
        self._last_swept = now

    def reset(self) -> None:
        """Test-only."""
        with self._lock:
            self._buckets.clear()

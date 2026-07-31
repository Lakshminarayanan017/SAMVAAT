"""Token budgets.

Three layers, because a single limit protects against a single failure:

  * **Per-user daily budget** — one learner, or one loop in the client, cannot
    exhaust the month for everyone else.
  * **Global daily budget** — a bug that fans out across users still hits a wall.
  * **The spend cap on the API key itself** — configured outside this codebase,
    and the only one that survives a bug in the other two. Set it on day one.

WHAT HAPPENS AT THE LIMIT
-------------------------
Nothing a learner would call an error. Generation stops; the scripted provider
takes over; the product keeps working. A learner who has practised enthusiastically
all afternoon must not be locked out as a reward — they get authored content for
the rest of the day and generated content again tomorrow.

The learner is told, once, in plain words, and never in a way that implies they
did something wrong.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Protocol

log = logging.getLogger("samvaad.genai.budget")

#: Roughly forty generated turns a day at typical sizes. Chosen to be generous:
#: an enthusiastic learner should hit it rarely, and a runaway loop should hit it
#: within a minute.
DEFAULT_DAILY_USER_TOKENS = 40_000

#: Across all learners. Sized for a pilot cohort of ~30 with headroom.
DEFAULT_DAILY_GLOBAL_TOKENS = 1_500_000


@dataclass
class Usage:
    day: date
    tokens: int = 0

    def add(self, tokens: int, today: date) -> None:
        if self.day != today:
            self.day = today
            self.tokens = 0
        self.tokens += tokens


class BudgetStore(Protocol):
    """The seam a Redis or Postgres implementation fills for multi-instance."""

    def usage(self, key: str, today: date) -> int: ...

    def record(self, key: str, tokens: int, today: date) -> None: ...


class InMemoryBudgetStore:
    """Correct for a single instance, which is what the free tier runs.

    Deliberately not silently wrong on multiple instances: `is_distributed` is
    False and the readiness probe surfaces it, so nobody discovers the gap while
    reading a surprising invoice.
    """

    is_distributed = False

    def __init__(self) -> None:
        self._usage: dict[str, Usage] = {}

    def usage(self, key: str, today: date) -> int:
        record = self._usage.get(key)
        if record is None or record.day != today:
            return 0
        return record.tokens

    def record(self, key: str, tokens: int, today: date) -> None:
        self._usage.setdefault(key, Usage(day=today)).add(tokens, today)

    def clear(self) -> None:
        self._usage.clear()


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    remaining: int
    #: Learner-facing, and only shown when generation actually stops.
    message: str = ""


@dataclass
class TokenBudget:
    """Checks and records spend."""

    store: BudgetStore = field(default_factory=InMemoryBudgetStore)
    daily_user_tokens: int = DEFAULT_DAILY_USER_TOKENS
    daily_global_tokens: int = DEFAULT_DAILY_GLOBAL_TOKENS

    GLOBAL_KEY = "__global__"

    def check(self, user_key: str, estimated_tokens: int, today: date | None = None) -> BudgetDecision:
        """Would this call fit inside both budgets?

        Checked before the call using an estimate, and recorded after using the
        real figure. Checking only afterwards means the call that breaks the
        budget is the one you already paid for.
        """
        today = today or datetime.now(timezone.utc).date()

        global_used = self.store.usage(self.GLOBAL_KEY, today)
        if global_used + estimated_tokens > self.daily_global_tokens:
            log.error("global daily token budget reached (%d)", global_used)
            return BudgetDecision(
                allowed=False,
                remaining=0,
                message=(
                    "The AI practice partner is resting for today. "
                    "Everything else still works, and it will be back tomorrow."
                ),
            )

        used = self.store.usage(user_key, today)
        remaining = self.daily_user_tokens - used

        if remaining < estimated_tokens:
            return BudgetDecision(
                allowed=False,
                remaining=max(0, remaining),
                message=(
                    "That is a lot of practice today — nicely done. "
                    "The AI partner takes a break now and will be back tomorrow. "
                    "Your drills and stories are still here."
                ),
            )

        return BudgetDecision(allowed=True, remaining=remaining)

    def record(self, user_key: str, tokens: int, today: date | None = None) -> None:
        today = today or datetime.now(timezone.utc).date()
        self.store.record(user_key, tokens, today)
        self.store.record(self.GLOBAL_KEY, tokens, today)

    def remaining(self, user_key: str, today: date | None = None) -> int:
        today = today or datetime.now(timezone.utc).date()
        return max(0, self.daily_user_tokens - self.store.usage(user_key, today))

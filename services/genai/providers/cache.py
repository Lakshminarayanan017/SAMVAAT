"""Response caching.

Identical context in, identical turn out. Two learners on the same scenario at
the same point with the same profile get the same NPC line, and we pay once.

This is worth more than it sounds. Role-play openings, interview questions and
scaffold generations repeat constantly across a cohort — the first turn of "first
day introduction" is generated once for thirty learners rather than thirty times.

WHY LRU AND NOT A TTL
---------------------
The cache key already contains the prompt hash, so a prompt version bump
invalidates everything derived from it automatically. There is nothing else in
the key that goes stale with time, and a TTL would only mean paying again for an
answer that was still correct.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Protocol

from providers.base import Completion

log = logging.getLogger("samvaad.genai.cache")

#: Entries held. Each is a few hundred bytes of JSON, so this is well under a
#: megabyte and sized for a pilot cohort's working set rather than for a guess.
DEFAULT_CAPACITY = 2_000


class CompletionCache(Protocol):
    def get(self, key: str) -> Completion | None: ...

    def put(self, key: str, completion: Completion) -> None: ...


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class LruCompletionCache:
    """In-process LRU.

    Correct for a single instance. On multiple instances each holds its own,
    which costs some duplicate spend but is never *wrong* — so unlike the rate
    limiter and the budget, this one degrades gracefully rather than failing
    open, and does not need a distributed implementation to be safe.
    """

    is_distributed = False

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self.capacity = capacity
        self._entries: OrderedDict[str, Completion] = OrderedDict()
        self.stats = CacheStats()

    def get(self, key: str) -> Completion | None:
        completion = self._entries.get(key)

        if completion is None:
            self.stats.misses += 1
            return None

        self._entries.move_to_end(key)
        self.stats.hits += 1

        # Flagged so the cost dashboard does not count it as spend, and so a
        # test can assert the cache is actually being used rather than assuming.
        return replace(completion, cached=True)

    def put(self, key: str, completion: Completion) -> None:
        # Scripted completions are free to produce and would only evict paid
        # ones from a bounded cache.
        if completion.scripted:
            return

        self._entries[key] = completion
        self._entries.move_to_end(key)

        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
        self.stats = CacheStats()

"""The LLM provider interface.

One interface, four implementations, and the rest of the service never knows
which one it is talking to:

    ClaudeProvider     production
    GroqProvider       free-tier development and fallback
    ScriptedProvider   no API key at all — the whole product on authored content
    RecordingProvider  wraps another and records for the eval fixtures

The reason this abstraction exists is not portability for its own sake. It is
that `ScriptedProvider` must be a first-class path rather than a degraded one:
CI must run the full role-play and interview flows without a key, and an API
outage must degrade to a working experience rather than an error screen. If the
scripted path were an afterthought it would be broken, and it would be broken on
exactly the day the outage happened.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("samvaad.genai.provider")


class LLMError(RuntimeError):
    """Any provider failure. Callers fall back rather than propagate."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        self.retryable = retryable
        super().__init__(message)


class BudgetExceeded(LLMError):
    """A per-user or global spend limit was reached.

    Not retryable, and deliberately a distinct type: the caller's response is to
    fall back to scripted content, not to wait and try again.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


@dataclass(frozen=True)
class Prompt:
    """A versioned, hashed prompt.

    The hash is persisted with every generation. Two years from now, "why did the
    rubric score this answer that way" has to be answerable, and the answer
    begins with knowing exactly which prompt produced it. A prompt edited in
    place with no version bump makes every past score uninterpretable.
    """

    name: str
    version: str
    system: str
    #: Few-shot exchanges, if any. Part of the hash — changing an example
    #: changes behaviour every bit as much as changing the instructions.
    examples: tuple[tuple[str, str], ...] = ()

    @property
    def hash(self) -> str:
        payload = json.dumps(
            {"name": self.name, "version": self.version, "system": self.system,
             "examples": list(self.examples)},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @property
    def id(self) -> str:
        return f"{self.name}@{self.version}#{self.hash}"


@dataclass(frozen=True)
class Completion:
    """What a provider returns.

    `raw` is the model's text. Callers parse it against a schema; nothing in the
    system trusts it before that.
    """

    raw: str
    model: str
    prompt_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    #: True when this came from the cache rather than the provider. Surfaced so
    #: the cost dashboard does not double-count, and so a test can assert the
    #: cache is actually being used.
    cached: bool = False
    #: True when no model was involved — authored content was served instead.
    scripted: bool = False

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class GenerationRequest:
    """One call. Deliberately small — providers do not see learner identity.

    `user_key` is an opaque budget key, not a user id: the provider layer needs
    to count spend per learner without knowing who the learner is. Sending a
    real identifier to a third-party API for the sole purpose of rate accounting
    would be a needless disclosure.
    """

    prompt: Prompt
    user_message: str
    user_key: str
    max_tokens: int = 700
    #: Zero by default. Every schema-constrained generation in this service wants
    #: determinism; variety comes from the retrieved context, not from sampling.
    temperature: float = 0.0
    #: Forces the model to begin its reply with this, which is how JSON output is
    #: made reliable without a function-calling round trip.
    prefill: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def cache_key(self) -> str:
        payload = json.dumps(
            {
                "prompt": self.prompt.id,
                "message": self.user_message,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "prefill": self.prefill,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LLMProvider(ABC):
    """The seam. Everything above this line is provider-agnostic."""

    #: Reported through `/capabilities` so the client can say what is available.
    name: str = "abstract"
    #: False for `ScriptedProvider`. The client uses this to label AI-generated
    #: content honestly — a learner is entitled to know when they are talking to
    #: a model and when they are reading something a person wrote.
    is_generative: bool = True

    @abstractmethod
    def complete(self, request: GenerationRequest) -> Completion:
        """Produce a completion, or raise `LLMError`."""

    def available(self) -> bool:
        """Whether this provider can be used right now."""
        return True

    def close(self) -> None:  # pragma: no cover - most providers hold nothing
        """Release any held resources."""

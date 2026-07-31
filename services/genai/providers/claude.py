"""The Claude provider.

Production. Lazily imported and probed, like every other heavy dependency in
this codebase, so the service boots and serves the scripted path with no SDK and
no key installed.

RETRY POLICY
------------
Two attempts, exponential backoff with jitter, and only on genuinely transient
failures. A 400 is our bug and retrying it wastes money; a 429 or a 529 is the
API asking us to wait. Retrying a schema failure is handled a layer up by the
guardrail chain's repair-retry, which sends a *different* message — retrying the
identical request would just produce the identical malformed answer.
"""

from __future__ import annotations

import logging
import os
import random
import time

from providers.base import BudgetExceeded, Completion, GenerationRequest, LLMError, LLMProvider

log = logging.getLogger("samvaad.genai.claude")

#: Sonnet for turns and rubric scoring; Haiku for classification sub-calls.
#: Using a frontier model to decide whether an utterance is on-topic is the
#: single easiest way to spend the budget on nothing.
DEFAULT_MODEL = "claude-sonnet-4-5"
CHEAP_MODEL = "claude-haiku-4-5-20251001"

MAX_ATTEMPTS = 2
BASE_BACKOFF_SECONDS = 0.5

#: Status codes worth waiting for. Everything else is ours to fix.
RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504, 529})


class ClaudeProvider(LLMProvider):
    name = "claude"
    is_generative = True

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = None

    def available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import anthropic  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self.api_key, timeout=self.timeout_seconds
            )
        return self._client

    def complete(self, request: GenerationRequest) -> Completion:
        if not self.available():
            raise LLMError("Claude provider unavailable: no API key or SDK", retryable=False)

        messages: list[dict] = []
        for user_text, assistant_text in request.prompt.examples:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})

        messages.append({"role": "user", "content": request.user_message})

        # Prefilling the assistant turn is how JSON output is made reliable:
        # the model cannot open with prose because its reply already began.
        if request.prefill:
            messages.append({"role": "assistant", "content": request.prefill})

        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._get_client().messages.create(
                    model=self.model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    system=request.prompt.system,
                    messages=messages,
                )

                text = "".join(
                    block.text for block in response.content if getattr(block, "type", "") == "text"
                )

                return Completion(
                    # The prefill is not echoed back by the API, so it has to be
                    # re-attached or every JSON parse fails on a missing brace.
                    raw=(request.prefill or "") + text,
                    model=self.model,
                    prompt_id=request.prompt.id,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )

            except Exception as error:  # noqa: BLE001 - normalised below
                last_error = error

                if _is_budget_error(error):
                    raise BudgetExceeded(str(error)) from error

                if not _is_retryable(error) or attempt == MAX_ATTEMPTS:
                    break

                # Jitter, so a burst of learners hitting a rate limit does not
                # retry in lockstep and hit it again together.
                delay = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(delay + random.uniform(0, delay * 0.3))
                log.warning("Claude call failed (%s); retry %d", type(error).__name__, attempt)

        raise LLMError(f"Claude call failed: {last_error}") from last_error


def _is_retryable(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    if status is not None:
        return status in RETRYABLE_STATUS

    # Connection and timeout errors carry no status. Their names are stable
    # enough to match on, and the cost of a wrong guess here is one extra
    # request rather than a wrong answer.
    return type(error).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
        "OverloadedError",
    }


def _is_budget_error(error: Exception) -> bool:
    """A hard spend cap on the key surfaces as a 400 with a specific message.

    Distinguished from an ordinary 400 because the response differs: a spend cap
    means fall back to scripted content for the rest of the month, not fix the
    request.
    """
    message = str(error).lower()
    return "credit balance" in message or "billing" in message or "spend limit" in message

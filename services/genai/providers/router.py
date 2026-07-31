"""Provider selection, caching, budgeting and fallback in one place.

Everything above this layer calls `generate()` and receives a `Completion`. It
never chooses a provider, never checks a budget, and never handles an outage,
because doing any of those in three feature modules means doing two of them
wrong.

THE ORDER OF OPERATIONS, AND WHY
--------------------------------
    1. cache        — free, and a hit skips everything below
    2. budget       — cheaper to refuse than to pay and then refuse
    3. provider     — the only step that costs money
    4. record spend — with the real token count, not the estimate
    5. on failure   — scripted fallback, always

Step 5 is not error handling bolted on. It is the product's normal behaviour in
an abnormal situation: a learner mid-interview gets the rest of their interview.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from providers.base import (
    BudgetExceeded,
    Completion,
    GenerationRequest,
    LLMError,
    LLMProvider,
)
from providers.budget import TokenBudget
from providers.cache import LruCompletionCache

log = logging.getLogger("samvaad.genai.router")

#: Rough characters-per-token for the estimate used in the pre-call budget
#: check. Deliberately conservative — over-estimating means refusing slightly
#: early, which is a far better failure than discovering the overspend after
#: paying for it.
CHARS_PER_TOKEN = 3.5


@dataclass
class GenerationResult:
    """A completion, plus how it was obtained.

    The provenance matters beyond debugging: the client labels content
    "AI-generated" only when a model was involved, and a learner is entitled to
    know which sentences a person wrote.
    """

    completion: Completion
    provider: str
    #: Set when the primary provider could not be used. Surfaced in logs and in
    #: the cost dashboard, never as an error to the learner.
    fallback_reason: str | None = None

    @property
    def is_generated(self) -> bool:
        return not self.completion.scripted


@dataclass
class ProviderRouter:
    """The single entry point for every generative call in this service."""

    primary: LLMProvider
    scripted: LLMProvider
    cache: LruCompletionCache = field(default_factory=LruCompletionCache)
    budget: TokenBudget = field(default_factory=TokenBudget)
    #: Optional second generative provider tried before falling back to
    #: authored content — a free-tier model in development, or a different
    #: vendor in production.
    secondary: LLMProvider | None = None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        cached = self.cache.get(request.cache_key())
        if cached is not None:
            return GenerationResult(completion=cached, provider=cached.model)

        estimate = self._estimate_tokens(request)
        decision = self.budget.check(request.user_key, estimate)

        if not decision.allowed:
            log.info("budget reached for %s; serving authored content", request.user_key)
            return self.fallback(request, "budget_exceeded", decision.message)

        for provider in self._generative_providers():
            try:
                completion = provider.complete(request)
            except BudgetExceeded as error:
                # The spend cap on the key itself. No other provider will help,
                # and retrying costs another rejected request.
                log.error("provider spend cap reached: %s", error)
                return self.fallback(request, "provider_spend_cap")
            except LLMError as error:
                log.warning("%s failed (%s); trying the next option", provider.name, error)
                continue

            self.budget.record(request.user_key, completion.total_tokens)
            self.cache.put(request.cache_key(), completion)

            return GenerationResult(completion=completion, provider=provider.name)

        return self.fallback(request, "all_providers_failed")

    def _generative_providers(self) -> list[LLMProvider]:
        candidates = [self.primary, self.secondary]
        return [p for p in candidates if p is not None and p.available()]

    def fallback(
        self,
        request: GenerationRequest,
        reason: str,
        message: str | None = None,
    ) -> GenerationResult:
        """Authored content. Never an error.

        If even this raises, the caller has asked for a prompt with no scripted
        responder, which is a programming error caught by a test — see
        `registered_prompts()`.
        """
        completion = self.scripted.complete(request)

        if message:
            request.metadata["budget_message"] = message

        return GenerationResult(
            completion=completion,
            provider=self.scripted.name,
            fallback_reason=reason,
        )

    def _estimate_tokens(self, request: GenerationRequest) -> int:
        prompt_chars = len(request.prompt.system) + sum(
            len(a) + len(b) for a, b in request.prompt.examples
        )
        input_estimate = (prompt_chars + len(request.user_message)) / CHARS_PER_TOKEN
        return int(input_estimate) + request.max_tokens

    def capabilities(self) -> dict[str, object]:
        """What this deployment can do, for `/capabilities`."""
        generative = self._generative_providers()

        return {
            "generative": bool(generative),
            "provider": generative[0].name if generative else self.scripted.name,
            "cache_hit_rate": round(self.cache.stats.hit_rate, 3),
            "distributed_cache": self.cache.is_distributed,
        }


def build_router(settings) -> ProviderRouter:
    """Assemble the router from configuration.

    Falls all the way back to scripted-only rather than raising when no key is
    present. A service that refuses to start without an API key cannot be run by
    a new developer, cannot be run in CI, and — on the day the key is rotated
    incorrectly — cannot be run at all.
    """
    from providers.claude import ClaudeProvider
    from providers.scripted import ScriptedProvider

    primary = ClaudeProvider(api_key=settings.anthropic_api_key, model=settings.llm_model)

    if not primary.available():
        log.warning(
            "No LLM provider is configured. The service is running on authored "
            "content only: every feature works, nothing is generated."
        )

    return ProviderRouter(
        primary=primary,
        scripted=ScriptedProvider(),
        budget=TokenBudget(
            daily_user_tokens=settings.daily_user_token_budget,
            daily_global_tokens=settings.daily_global_token_budget,
        ),
    )

"""Shared fixtures for the GenAI service.

Every test here runs with NO API key, no network and no model download. That is
not a limitation of the test environment — it is the configuration the service
is designed to work in, and testing it is how we know the scripted path is
genuinely good rather than merely present.

A test that needs a real provider is the exception and says so.
"""

from __future__ import annotations

import pytest

from providers.base import Completion, GenerationRequest, LLMError, LLMProvider
from providers.router import ProviderRouter
from providers.scripted import ScriptedProvider


class UnavailableProvider(LLMProvider):
    """Stands in for a provider with no key configured."""

    name = "unavailable"

    def available(self) -> bool:
        return False

    def complete(self, request: GenerationRequest) -> Completion:  # pragma: no cover
        raise LLMError("not configured", retryable=False)


class FailingProvider(LLMProvider):
    """Available, and fails. Exercises the outage path.

    Distinct from `UnavailableProvider` because the two take different routes
    through the router, and the one that matters during a real incident is this
    one — a provider that is configured, reachable and returning errors.
    """

    name = "failing"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, request: GenerationRequest) -> Completion:
        self.calls += 1
        raise LLMError("upstream is having a bad day")


class StubProvider(LLMProvider):
    """Returns a fixed payload, so guardrail and parsing behaviour can be tested
    without a model in the loop."""

    name = "stub"

    def __init__(self, payloads: list[str]) -> None:
        self.payloads = list(payloads)
        self.requests: list[GenerationRequest] = []

    def complete(self, request: GenerationRequest) -> Completion:
        self.requests.append(request)
        raw = self.payloads.pop(0) if self.payloads else "{}"
        return Completion(
            raw=raw,
            model="stub",
            prompt_id=request.prompt.id,
            input_tokens=100,
            output_tokens=50,
        )


@pytest.fixture
def scripted() -> ScriptedProvider:
    return ScriptedProvider()


@pytest.fixture
def router(scripted: ScriptedProvider) -> ProviderRouter:
    """The default configuration: no key, authored content."""
    return ProviderRouter(primary=UnavailableProvider(), scripted=scripted)


@pytest.fixture
def stub_router(scripted: ScriptedProvider):
    """Build a router around a stubbed generative provider."""

    def build(payloads: list[str]) -> tuple[ProviderRouter, StubProvider]:
        provider = StubProvider(payloads)
        return ProviderRouter(primary=provider, scripted=scripted), provider

    return build


@pytest.fixture
def failing_router(scripted: ScriptedProvider) -> tuple[ProviderRouter, FailingProvider]:
    provider = FailingProvider()
    return ProviderRouter(primary=provider, scripted=scripted), provider

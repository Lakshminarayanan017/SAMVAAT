"""Client for the GenAI service.

The GenAI service is stateless by design: conversation state travels with every
request. That makes it restartable and scale-to-zero-able, and it puts the
responsibility for persistence here, in the gateway — which is the only thing
that talks to the database (ADR-0004).

DEGRADATION IS HONEST, NOT SILENT
---------------------------------
Every call can fail, because it depends on a free-tier host and a paid LLM. When
it does, this client raises `GenAiUnavailable` carrying a message written for a
learner, and the router turns that into a 503 with a plain explanation.

It never returns an empty result that looks like a successful one. A learner
staring at a blank interview screen has no way to tell "the service is down"
from "I did something wrong", and will assume the latter.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger("samvaad.api.genai")

#: Generous. LLM turns are slow, and cutting one off mid-generation gives the
#: learner a broken screen rather than a slow one. This is a ceiling on our own
#: patience, never a limit on how long the learner may take (Ethics E6).
TURN_TIMEOUT_SECONDS = 45.0
QUICK_TIMEOUT_SECONDS = 10.0


class GenAiUnavailable(RuntimeError):
    """The GenAI service could not answer. Carries learner-facing copy."""

    def __init__(self, detail: str, learner_message: str | None = None) -> None:
        self.detail = detail
        self.learner_message = learner_message or (
            "Practice conversations are resting just now. Everything else still works — "
            "try a drill, and come back to this in a little while."
        )
        super().__init__(detail)


class GenAiClient:
    """Thin, typed wrapper. One method per GenAI route we actually use."""

    def __init__(self, base_url: str | None = None, service_token: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.genai_service_url).rstrip("/")
        self.service_token = service_token or settings.service_token

    # ── plumbing ─────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        # Unset in development so a fresh clone runs with no configuration. The
        # services themselves fail closed in production, so this cannot become a
        # silent bypass.
        return {"X-Service-Token": self.service_token} if self.service_token else {}

    async def _post(self, path: str, payload: dict, timeout: float) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}{path}", json=payload, headers=self._headers()
                )
        except httpx.TimeoutException as error:
            raise GenAiUnavailable(f"timeout calling {path}") from error
        except httpx.HTTPError as error:
            raise GenAiUnavailable(f"{type(error).__name__} calling {path}") from error

        return self._unwrap(response, path)

    async def _get(self, path: str, timeout: float, **params: Any) -> Any:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    f"{self.base_url}{path}", params=params, headers=self._headers()
                )
        except httpx.HTTPError as error:
            raise GenAiUnavailable(f"{type(error).__name__} calling {path}") from error

        return self._unwrap(response, path)

    @staticmethod
    def _unwrap(response: httpx.Response, path: str) -> Any:
        if response.status_code == 401:
            # Ours to fix, never the learner's. Loud in the log, gentle on screen.
            log.error("genai rejected our service token on %s", path)
            raise GenAiUnavailable("service token rejected")

        if response.status_code >= 500:
            raise GenAiUnavailable(f"genai returned {response.status_code} on {path}")

        if response.status_code >= 400:
            # A 4xx is our bug — a malformed request — so it must not be dressed
            # up as a transient outage that will fix itself.
            log.error("genai rejected %s: %s", path, response.text[:400])
            raise GenAiUnavailable(f"genai rejected the request to {path}")

        return response.json()

    # ── capability ───────────────────────────────────────────────────────────

    async def capabilities(self) -> dict[str, Any]:
        """What the GenAI service can do right now.

        Returns an all-false shape rather than raising, because the client asks
        this precisely so it can render an honest "unavailable" state.
        """
        try:
            return await self._get("/capabilities", QUICK_TIMEOUT_SECONDS)
        except GenAiUnavailable:
            return {"generative": False, "provider": "unavailable", "scenarios": 0}

    async def scenarios(self) -> list[dict]:
        return await self._get("/scenarios", QUICK_TIMEOUT_SECONDS)

    # ── role-play ────────────────────────────────────────────────────────────

    async def open_roleplay(self, scenario_id: str, difficulty: int, persona: str) -> dict:
        return await self._post(
            "/roleplay/open",
            {"scenario_id": scenario_id, "difficulty": difficulty, "persona": persona},
            TURN_TIMEOUT_SECONDS,
        )

    async def roleplay_respond(
        self,
        state: dict,
        learner_text: str,
        met_expectation: bool,
        text_complexity: str,
    ) -> dict:
        return await self._post(
            "/roleplay/respond",
            {
                "state": state,
                "learner_text": learner_text,
                "met_expectation": met_expectation,
                "text_complexity": text_complexity,
            },
            TURN_TIMEOUT_SECONDS,
        )

    # ── interview ────────────────────────────────────────────────────────────

    async def interview_start(
        self,
        interview_id: str,
        track: str,
        persona: str,
        target_questions: int,
        job_context: str,
    ) -> dict:
        return await self._post(
            "/interview/start",
            {
                "interview_id": interview_id,
                "track": track,
                "persona": persona,
                "target_questions": target_questions,
                "job_context": job_context,
            },
            TURN_TIMEOUT_SECONDS,
        )

    async def interview_next(self, state: dict, answer: str | None) -> dict:
        return await self._post(
            "/interview/next",
            {"state": state, "answer": answer},
            TURN_TIMEOUT_SECONDS,
        )

    async def interview_pause(self, state: dict) -> dict:
        return await self._post("/interview/pause", {"state": state}, QUICK_TIMEOUT_SECONDS)

    async def disclosure(self, step: str) -> dict:
        return await self._get("/interview/disclosure", QUICK_TIMEOUT_SECONDS, step=step)

    async def score(self, question: str, answer: str, role_context: str) -> dict:
        return await self._post(
            "/rubric/score",
            {"question": question, "answer": answer, "role_context": role_context},
            TURN_TIMEOUT_SECONDS,
        )

    # ── stories ──────────────────────────────────────────────────────────────

    async def story(
        self, job_context: str, situation: str, reading_level: str, has_trainer: bool
    ) -> dict:
        return await self._post(
            "/stories",
            {
                "job_context": job_context,
                "situation": situation,
                "reading_level": reading_level,
                "has_trainer": has_trainer,
            },
            TURN_TIMEOUT_SECONDS,
        )

"""SAMVAAD GenAI service.

Role-play (M9), social stories (M10) and the bias-guarded interview rubric (M11).

Separate from the API gateway because this is the one component with an external
paid dependency and non-deterministic output — which makes it the one component
worth being able to test, budget, rate-limit and swap independently (ADR-0004).

EVERY RESPONSE IS A ContentBlock
--------------------------------
Nothing here decides how anything looks. The engine emits meaning and
representations; the client's Modality Router picks the channel from the
learner's profile. That is why one generated turn becomes free-form conversation
for P1, a three-choice tap for P4, and captions plus ISL for P2.

THE SERVICE RUNS WITH NO API KEY
--------------------------------
Without one it serves authored content, reports `generative: false` through
`/capabilities`, and every feature still works end to end. That is a supported
configuration, not a degraded one — CI runs in it, and so does an outage.
"""

from __future__ import annotations

import logging
import time
from typing import Annotated, Literal

from fastapi import Body, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from samvaad_platform import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
    install_error_handlers,
    service_token_dependency,
)

from service.config import get_settings

configure_logging("samvaad-genai")
log = logging.getLogger("samvaad.genai")

_STARTED_AT = time.monotonic()

require_service_token = service_token_dependency()


# ── models ───────────────────────────────────────────────────────────────────


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    uptime_seconds: float


class Capabilities(BaseModel):
    generative: bool = False
    provider: str = "scripted"
    semantic_retrieval: bool = False
    cache_hit_rate: float = 0.0
    distributed_cache: bool = False
    scenarios: int = 0
    rubric_version: str = ""


class ScenarioSummary(BaseModel):
    id: str
    title: str
    role: str
    setting: str
    goal: str
    #: Emotionally loaded scenarios get an explicit exit and a route to a human.
    sensitive: bool = False


class TurnStatePayload(BaseModel):
    """The conversation state, round-tripped through the client.

    The service is stateless: state goes out with the response and comes back
    with the next request. A conversation survives a redeploy mid-sentence, and
    there is no server-side session to expire while a learner is thinking.
    """

    scenario_id: str
    difficulty: int = Field(default=2, ge=1, le=5)
    turn_number: int = Field(default=0, ge=0)
    history: list[dict] = Field(default_factory=list)
    outcomes: list[bool] = Field(default_factory=list)
    error_signature: list[str] = Field(default_factory=list)
    goal_met: bool = False
    persona: str = "supportive"


class OpenRequest(BaseModel):
    scenario_id: str
    difficulty: int = Field(default=2, ge=1, le=5)
    persona: Literal["supportive", "neutral", "brisk"] = "supportive"


class RespondRequest(BaseModel):
    state: TurnStatePayload
    learner_text: str = Field(max_length=4000)
    #: Whether the learner's reply did what the previous turn expected. Drives
    #: the ZPD difficulty adjustment.
    met_expectation: bool = True
    text_complexity: Literal["standard", "easy_read"] = "standard"


class TurnResponse(BaseModel):
    #: Rendered by the Modality Router. The service never chooses a channel.
    block: dict
    state: TurnStatePayload
    #: True only when a model produced this. The client labels AI content
    #: honestly — a learner is entitled to know which sentences a person wrote.
    generated: bool
    provider: str
    guardrails: dict = Field(default_factory=dict)
    #: Set when a budget or outage changed what the learner got. Shown once, in
    #: plain words, and never as though they did something wrong.
    notice: str | None = None


class StoryRequest(BaseModel):
    job_context: str = Field(max_length=200)
    situation: str = Field(max_length=300)
    reading_level: Literal["standard", "easy_read"] = "easy_read"
    #: Stories stay in draft until a trainer approves, when the learner has one.
    has_trainer: bool = False


class StoryResponse(BaseModel):
    title: str
    panels: list[dict]
    status: Literal["draft", "published"]
    generated: bool
    validation: dict
    notice: str | None = None


class InterviewStatePayload(BaseModel):
    """The interview, round-tripped through the client.

    Note what has no field here: any timestamp of when a question was asked or
    answered, any duration, any per-question clock. Ethics E6 is enforced by the
    shape of this model — nothing downstream can score response latency because
    nothing records it.
    """

    interview_id: str
    track: Literal["hr", "role", "telephonic"] = "hr"
    persona: Literal["supportive", "neutral", "brisk"] = "supportive"
    exchanges: list[dict] = Field(default_factory=list)
    target_questions: int = Field(default=10, ge=8, le=12)
    status: Literal["in_progress", "paused", "complete"] = "in_progress"
    started_at: str = ""
    job_context: str = ""


class InterviewStartRequest(BaseModel):
    interview_id: str
    track: Literal["hr", "role", "telephonic"] = "hr"
    persona: Literal["supportive", "neutral", "brisk"] = "supportive"
    target_questions: int = Field(default=10, ge=8, le=12)
    job_context: str = Field(default="", max_length=200)


class InterviewNextRequest(BaseModel):
    state: InterviewStatePayload
    #: The answer to the question currently on screen, if there is one.
    answer: str | None = Field(default=None, max_length=8000)


class InterviewQuestionResponse(BaseModel):
    block: dict
    state: InterviewStatePayload
    generated: bool
    provider: str
    finished: bool = False
    #: Progress, never pressure. "Question 4 of about 10", never a countdown.
    progress: str = ""


class ScoreRequest(BaseModel):
    question: str = Field(max_length=1000)
    answer: str = Field(max_length=8000)
    role_context: str = Field(default="", max_length=500)


class ScoreResponse(BaseModel):
    scored: bool
    dimensions: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    unavailable_message: str = ""
    #: Layer 4 of the E2 enforcement. Persisted by the API alongside the score.
    audit: dict = Field(default_factory=dict)


# ── app ──────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SAMVAAD GenAI Service",
        version=settings.version,
        description=(
            "RAG-grounded role-play, social stories and the bias-guarded interview "
            "rubric. Stateless: conversation state travels with the request."
        ),
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    install_error_handlers(app)

    for problem in settings.check_production():
        log.error("production configuration problem: %s", problem)

    @app.get("/healthz", response_model=Health, summary="Liveness probe")
    async def healthz() -> Health:
        return Health(
            service=settings.service_name,
            version=settings.version,
            uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
        )

    @app.get("/capabilities", response_model=Capabilities, summary="What is live")
    async def capabilities() -> Capabilities:
        from retrieval.index import embeddings_available
        from roleplay import scenarios

        return Capabilities(
            **_router().capabilities(),
            semantic_retrieval=embeddings_available(),
            scenarios=len(scenarios.SCENARIOS),
            rubric_version=settings.rubric_version,
        )

    @app.get("/scenarios", response_model=list[ScenarioSummary], summary="The scenario library")
    async def list_scenarios() -> list[ScenarioSummary]:
        from roleplay import scenarios

        return [
            ScenarioSummary(
                id=s.id,
                title=s.title,
                role=s.role,
                setting=s.setting,
                goal=s.goal,
                sensitive=s.sensitive,
            )
            for s in scenarios.all_scenarios()
        ]

    @app.post(
        "/roleplay/open",
        response_model=TurnResponse,
        summary="Start a role-play",
        dependencies=[Depends(require_service_token)],
    )
    async def open_roleplay(request: Annotated[OpenRequest, Body()]) -> TurnResponse:
        try:
            result = _engine().open(request.scenario_id, request.difficulty, request.persona)
        except KeyError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail={"error": "unknown_scenario", "message": "We could not find that practice."},
            ) from error

        return _turn_response(result)

    @app.post(
        "/roleplay/respond",
        response_model=TurnResponse,
        summary="The next turn",
        dependencies=[Depends(require_service_token)],
    )
    async def respond(request: Annotated[RespondRequest, Body()]) -> TurnResponse:
        from roleplay.engine import ConversationState, Turn

        state = ConversationState(
            scenario_id=request.state.scenario_id,
            difficulty=request.state.difficulty,
            turn_number=request.state.turn_number,
            history=[Turn(**turn) for turn in request.state.history],
            outcomes=list(request.state.outcomes),
            error_signature=tuple(request.state.error_signature),
            goal_met=request.state.goal_met,
            persona=request.state.persona,
        )

        try:
            result = _engine().respond(state, request.learner_text, request.met_expectation)
        except KeyError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail={"error": "unknown_scenario", "message": "We could not find that practice."},
            ) from error

        return _turn_response(result)

    @app.post(
        "/stories",
        response_model=StoryResponse,
        summary="Generate a social story",
        dependencies=[Depends(require_service_token)],
    )
    async def generate_story(request: Annotated[StoryRequest, Body()]) -> StoryResponse:
        from stories.generator import StoryGenerator

        result = StoryGenerator(_router()).generate(
            job_context=request.job_context,
            situation=request.situation,
            reading_level=request.reading_level,
            has_trainer=request.has_trainer,
        )

        return StoryResponse(
            title=result.title,
            panels=[panel.as_dict() for panel in result.panels],
            status=result.status,
            generated=result.generated,
            validation=result.validation.as_dict(),
            notice=result.notice,
        )

    @app.post(
        "/interview/start",
        response_model=InterviewQuestionResponse,
        summary="Begin a mock interview",
        dependencies=[Depends(require_service_token)],
    )
    async def start_interview(
        request: Annotated[InterviewStartRequest, Body()],
    ) -> InterviewQuestionResponse:
        runner = _interview_runner()

        state = runner.start(
            interview_id=request.interview_id,
            track=request.track,
            persona=request.persona,
            target_questions=request.target_questions,
            job_context=request.job_context,
        )

        return _interview_response(runner.next_question(state))

    @app.post(
        "/interview/next",
        response_model=InterviewQuestionResponse,
        summary="Record an answer and get the next question",
        dependencies=[Depends(require_service_token)],
    )
    async def next_interview_question(
        request: Annotated[InterviewNextRequest, Body()],
    ) -> InterviewQuestionResponse:
        from interview.runner import Exchange, InterviewState

        runner = _interview_runner()

        state = InterviewState(
            interview_id=request.state.interview_id,
            track=request.state.track,
            persona=request.state.persona,
            exchanges=[Exchange(**exchange) for exchange in request.state.exchanges],
            target_questions=request.state.target_questions,
            status=request.state.status,
            started_at=request.state.started_at,
            job_context=request.state.job_context,
        )

        if request.answer is not None:
            state = runner.record_answer(state, request.answer)

        return _interview_response(runner.next_question(state))

    @app.post(
        "/interview/pause",
        response_model=InterviewStatePayload,
        summary="Pause an interview",
        dependencies=[Depends(require_service_token)],
    )
    async def pause_interview(
        state: Annotated[InterviewStatePayload, Body()],
    ) -> InterviewStatePayload:
        """Stop wherever the learner is.

        No penalty, no expiry, no warning. A learner with anxiety or fatigue may
        need to stop mid-answer and come back tomorrow, and an interview that
        cannot be paused is one P4 and P5 will not finish.
        """
        return state.model_copy(update={"status": "paused"})

    @app.get(
        "/interview/disclosure",
        summary="The accommodation and disclosure coach",
    )
    async def disclosure_coach(step: str = "considerations") -> dict:
        """The feature no competitor has.

        Never advises whether to disclose — that is the learner's decision about
        their own life, and it depends on facts we do not have. It lays out
        paired considerations, offers phrasings with what each one gives away
        stated plainly, and rehearses both the good employer response and the
        bad one.
        """
        from interview import disclosure

        if step == "phrasing":
            payload: dict = {"phrasings": disclosure.phrasings()}
        elif step == "rights":
            payload = disclosure.rights_primer()
        elif step in {"supportive", "neutral", "poor"}:
            payload = disclosure.branch(step)  # type: ignore[arg-type]
        else:
            payload = {"considerations": disclosure.considerations()}

        # Every screen carries a way out and a route to a person. This content is
        # emotionally loaded and a learner may find mid-way that they do not want
        # to do it today.
        payload.setdefault("exit_offer", disclosure.EXIT_OFFER)
        return payload

    @app.post(
        "/rubric/score",
        response_model=ScoreResponse,
        summary="Score one interview answer",
        dependencies=[Depends(require_service_token)],
    )
    async def score(request: Annotated[ScoreRequest, Body()]) -> ScoreResponse:
        """The bias-guarded rubric.

        Note what this endpoint does NOT accept: no timing, no audio reference,
        no prosody, no disfluency events. Not because a caller is trusted not to
        send them, but because there is no field for them to arrive in. Layer 1
        of the Ethics E2 enforcement starts at the request model.
        """
        from rubric.scorer import RubricScorer

        result = RubricScorer(
            _router(), runs=settings.rubric_self_consistency_runs, version=settings.rubric_version
        ).score(request.question, request.answer, request.role_context)

        return ScoreResponse(
            scored=result.scored,
            dimensions=[
                {
                    "dimension": d.dimension.value,
                    "label": d.learner_label,
                    "score": d.score,
                    "evidence": d.evidence,
                    "stable": d.is_stable,
                }
                for d in result.dimensions
            ],
            strengths=list(result.strengths),
            improvements=list(result.improvements),
            unavailable_message=result.unavailable_message,
            audit=result.audit,
        )

    return app


# ── singletons ───────────────────────────────────────────────────────────────
#
# Built once, lazily. The phrase index and the embedding model are both
# expensive to construct and immutable once built, and rebuilding either per
# request would dominate the latency of every turn.


_ROUTER = None
_ENGINE = None
_INTERVIEW = None


def _router():
    global _ROUTER
    if _ROUTER is None:
        from providers.router import build_router

        _ROUTER = build_router(get_settings())
    return _ROUTER


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from roleplay.engine import RolePlayEngine

        _ENGINE = RolePlayEngine(_router())
    return _ENGINE


def _interview_runner():
    global _INTERVIEW
    if _INTERVIEW is None:
        from interview.runner import InterviewRunner

        _INTERVIEW = InterviewRunner(_router())
    return _INTERVIEW


def _interview_response(result) -> InterviewQuestionResponse:
    from dataclasses import asdict

    return InterviewQuestionResponse(
        block=result.block,
        state=InterviewStatePayload(
            interview_id=result.state.interview_id,
            track=result.state.track,
            persona=result.state.persona,
            exchanges=[asdict(exchange) for exchange in result.state.exchanges],
            target_questions=result.state.target_questions,
            status=result.state.status,
            started_at=result.state.started_at,
            job_context=result.state.job_context,
        ),
        generated=result.generated,
        provider=result.provider,
        finished=result.finished,
        progress=result.state.progress_message(),
    )


def _turn_response(result) -> TurnResponse:
    return TurnResponse(
        block=result.block,
        state=TurnStatePayload(
            scenario_id=result.state.scenario_id,
            difficulty=result.state.difficulty,
            turn_number=result.state.turn_number,
            history=[{"speaker": t.speaker, "text": t.text} for t in result.state.history],
            outcomes=list(result.state.outcomes),
            error_signature=list(result.state.error_signature),
            goal_met=result.state.goal_met,
            persona=result.state.persona,
        ),
        generated=result.generated,
        provider=result.provider,
        guardrails=result.guardrails.audit(),
    )


app = create_app()

"""Role-play and mock-interview endpoints (M9, M11).

The learner-facing surface for the two features that were, until now, built and
unreachable. The gateway holds conversation state; the GenAI service holds none.

THREE RULES THIS ROUTER ENFORCES
--------------------------------
1. **Pause and resume always work** (Ethics E6). An interview can be stopped at
   any question and picked up later. A learner with fatigue, anxiety or a
   fluctuating condition should never have to finish in one sitting, and one who
   loses their connection should not lose their place.

2. **Degradation is honest.** When the GenAI service cannot answer, this returns
   503 with a plain sentence and a pointer at what still works. It never returns
   an empty success — a learner staring at a blank screen has no way to tell "the
   service is down" from "I did something wrong", and will assume the latter.

3. **The rubric audit record is persisted with every score** (Ethics E2, layer
   four). The GenAI service produces it; storing it is what makes the fairness
   claim auditable two years later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.learning.conversations import Conversation
from app.repositories.learners import AuditRepository, ConversationRepository
from app.security.auth import CurrentUser
from app.services.genai_client import GenAiClient, GenAiUnavailable

router = APIRouter(tags=["conversation"])

Session = Annotated[AsyncSession, Depends(get_session)]
_client = GenAiClient()


def _unavailable(error: GenAiUnavailable) -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"error": "genai_unavailable", "message": error.learner_message},
    )


async def _load(session: AsyncSession, conversation_id: str, user_id: str) -> Conversation:
    """Scoped on user_id in the query itself, so there is no path here that CAN
    return someone else's conversation.

    A missing row and someone else's row are indistinguishable from outside,
    so conversation ids cannot be probed for existence.
    """
    conversation = await ConversationRepository(session).get(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such conversation")
    return conversation


# ── role-play (M9) ───────────────────────────────────────────────────────────


class OpenRoleplayRequest(BaseModel):
    scenario_id: str
    difficulty: int = Field(default=2, ge=1, le=5)
    persona: Literal["supportive", "neutral", "brisk"] = "supportive"


class ReplyRequest(BaseModel):
    text: str = Field(max_length=4000)
    met_expectation: bool = True
    text_complexity: Literal["standard", "easy_read"] = "standard"


class TurnResponse(BaseModel):
    conversation_id: str
    block: dict
    generated: bool
    provider: str
    guardrails: dict = Field(default_factory=dict)
    notice: str | None = None
    finished: bool = False


@router.get("/scenarios", summary="The scenario library")
async def scenarios() -> list[dict]:
    try:
        return await _client.scenarios()
    except GenAiUnavailable as error:
        raise _unavailable(error) from error


@router.post("/roleplay/start", response_model=TurnResponse, summary="Open a role-play")
async def start_roleplay(
    principal: CurrentUser,
    session: Session,
    request: Annotated[OpenRoleplayRequest, Body()],
) -> TurnResponse:
    try:
        result = await _client.open_roleplay(
            request.scenario_id, request.difficulty, request.persona
        )
    except GenAiUnavailable as error:
        raise _unavailable(error) from error

    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=f"rp_{uuid4().hex[:12]}",
        user_id=principal.user_id,
        kind="roleplay",
        state=result["state"],
        created_at=now,
        updated_at=now,
    )
    await ConversationRepository(session).save(conversation)

    return TurnResponse(
        conversation_id=conversation.id,
        block=result["block"],
        generated=result.get("generated", False),
        provider=result.get("provider", "scripted"),
        guardrails=result.get("guardrails", {}),
        notice=result.get("notice"),
    )


@router.post(
    "/roleplay/{conversation_id}/reply",
    response_model=TurnResponse,
    summary="Take a turn",
)
async def reply(
    conversation_id: str,
    principal: CurrentUser,
    session: Session,
    request: Annotated[ReplyRequest, Body()],
) -> TurnResponse:
    conversation = await _load(session, conversation_id, principal.user_id)

    try:
        result = await _client.roleplay_respond(
            conversation.state,
            request.text,
            request.met_expectation,
            request.text_complexity,
        )
    except GenAiUnavailable as error:
        # State is untouched, so the learner can retry the same turn once the
        # service recovers. Losing their place because a host slept would be a
        # cruel way to end a conversation they found hard to start.
        raise _unavailable(error) from error

    conversation.state = result["state"]
    conversation.exchanges.append({"learner": request.text, "npc": result["block"]})
    await ConversationRepository(session).save(conversation)

    return TurnResponse(
        conversation_id=conversation.id,
        block=result["block"],
        generated=result.get("generated", False),
        provider=result.get("provider", "scripted"),
        guardrails=result.get("guardrails", {}),
        notice=result.get("notice"),
        finished=bool(result["state"].get("goal_met")),
    )


# ── mock interview (M11) ─────────────────────────────────────────────────────


class StartInterviewRequest(BaseModel):
    track: Literal["hr", "role", "telephonic"] = "hr"
    persona: Literal["supportive", "neutral", "brisk"] = "supportive"
    target_questions: int = Field(default=10, ge=8, le=12)
    job_context: str = Field(default="", max_length=200)


class AnswerRequest(BaseModel):
    #: Absent means "ask the first question". Present means "here is my answer,
    #: now ask the next one".
    answer: str | None = Field(default=None, max_length=8000)


class QuestionResponse(BaseModel):
    conversation_id: str
    block: dict
    generated: bool
    provider: str
    finished: bool = False
    #: "Question 4 of about 10" — progress, never a countdown (Ethics E6).
    progress: str = ""


@router.post("/interview/start", response_model=QuestionResponse, summary="Begin an interview")
async def start_interview(
    principal: CurrentUser,
    session: Session,
    request: Annotated[StartInterviewRequest, Body()],
) -> QuestionResponse:
    interview_id = f"iv_{uuid4().hex[:12]}"

    try:
        result = await _client.interview_start(
            interview_id,
            request.track,
            request.persona,
            request.target_questions,
            request.job_context,
        )
    except GenAiUnavailable as error:
        raise _unavailable(error) from error

    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=interview_id,
        user_id=principal.user_id,
        kind="interview",
        state=result["state"],
        created_at=now,
        updated_at=now,
    )
    await ConversationRepository(session).save(conversation)

    return QuestionResponse(
        conversation_id=interview_id,
        block=result["block"],
        generated=result.get("generated", False),
        provider=result.get("provider", "scripted"),
        finished=result.get("finished", False),
        progress=result.get("progress", ""),
    )


@router.post(
    "/interview/{conversation_id}/answer",
    response_model=QuestionResponse,
    summary="Answer, and get the next question",
)
async def answer(
    conversation_id: str,
    principal: CurrentUser,
    session: Session,
    request: Annotated[AnswerRequest, Body()],
) -> QuestionResponse:
    conversation = await _load(session, conversation_id, principal.user_id)

    if conversation.finished:
        raise HTTPException(status.HTTP_409_CONFLICT, "This interview is already finished")

    try:
        result = await _client.interview_next(conversation.state, request.answer)
    except GenAiUnavailable as error:
        raise _unavailable(error) from error

    conversation.state = result["state"]
    if request.answer is not None:
        conversation.exchanges.append({"answer": request.answer})
    conversation.finished = bool(result.get("finished"))
    await ConversationRepository(session).save(conversation)

    return QuestionResponse(
        conversation_id=conversation.id,
        block=result["block"],
        generated=result.get("generated", False),
        provider=result.get("provider", "scripted"),
        finished=conversation.finished,
        progress=result.get("progress", ""),
    )


@router.post("/interview/{conversation_id}/pause", summary="Pause, keeping your place")
async def pause(conversation_id: str, principal: CurrentUser, session: Session) -> dict:
    """Ethics E6. Stopping must never cost the learner their progress."""
    conversation = await _load(session, conversation_id, principal.user_id)

    try:
        result = await _client.interview_pause(conversation.state)
        conversation.state = result.get("state", conversation.state)
    except GenAiUnavailable:
        # Pausing is the one thing that must work even when the GenAI service is
        # down. The state is already ours; marking it paused needs nobody's help.
        conversation.state = {**conversation.state, "status": "paused"}
        result = {}

    await ConversationRepository(session).save(conversation)

    return {
        "conversation_id": conversation.id,
        "status": "paused",
        "message": result.get("message")
        or "Paused. Your place is saved — come back whenever you are ready.",
    }


@router.get("/interview/{conversation_id}", summary="Resume, or review")
async def get_interview(
    conversation_id: str, principal: CurrentUser, session: Session
) -> dict:
    conversation = await _load(session, conversation_id, principal.user_id)
    return {
        "conversation_id": conversation.id,
        "kind": conversation.kind,
        "finished": conversation.finished,
        "exchanges": conversation.exchanges,
        "state": conversation.state,
        "updated_at": conversation.updated_at,
    }


@router.get("/interviews", summary="A learner's interviews")
async def list_interviews(principal: CurrentUser, session: Session) -> list[dict]:
    conversations = await ConversationRepository(session).list_for_user(
        principal.user_id, kind="interview"
    )
    return [
        {
            "conversation_id": c.id,
            "finished": c.finished,
            "questions_answered": len(c.exchanges),
            "updated_at": c.updated_at,
        }
        for c in conversations
    ]


# ── scoring (M11, the bias-guarded rubric) ───────────────────────────────────


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
    audit_id: str | None = None


@router.post("/interview/score", response_model=ScoreResponse, summary="Score one answer")
async def score(
    principal: CurrentUser,
    session: Session,
    request: Annotated[ScoreRequest, Body()],
) -> ScoreResponse:
    try:
        result = await _client.score(request.question, request.answer, request.role_context)
    except GenAiUnavailable as error:
        raise _unavailable(error) from error

    audit_id = None
    if result.get("audit"):
        # Layer four of the E2 enforcement. The GenAI service proves the rubric
        # was blind to speech traits; persisting the record is what makes that
        # provable later, to someone who was not in the room.
        audit_id = f"aud_{uuid4().hex[:12]}"
        await AuditRepository(session).record(
            audit_id, principal.user_id, result["audit"], conversation_id=None
        )

    return ScoreResponse(
        scored=result.get("scored", False),
        dimensions=result.get("dimensions", []),
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        unavailable_message=result.get("unavailable_message", ""),
        audit_id=audit_id,
    )


@router.get("/interview/audit/{audit_id}", summary="Retrieve a rubric audit record")
async def audit_record(audit_id: str, principal: CurrentUser, session: Session) -> dict:
    # Scoped to the caller: an audit record is a statement about one
    # learner's interview, and nobody else may read it.
    record = await AuditRepository(session).get(audit_id, principal.user_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such audit record")

    return {
        "id": record.id,
        "rubric_version": record.rubric_version,
        "scored_dimensions": record.scored_dimensions,
        "excluded_dimensions": record.excluded_dimensions,
        "prompt_hash": record.prompt_hash,
        "model_id": record.model_id,
        "at": record.at,
    }


# ── the accommodation & disclosure coach (M11) ───────────────────────────────


@router.get("/disclosure", summary="Rehearse asking for an adjustment")
async def disclosure(step: str = "considerations") -> dict:
    """The conversation no other communication trainer covers, and the one that
    most decides whether a disabled person keeps a job."""
    try:
        return await _client.disclosure(step)
    except GenAiUnavailable as error:
        raise _unavailable(error) from error


# ── social stories (M10) ─────────────────────────────────────────────────────


class StoryRequest(BaseModel):
    job_context: str = Field(max_length=200)
    situation: str = Field(max_length=300)
    reading_level: Literal["standard", "easy_read"] = "easy_read"
    has_trainer: bool = False


@router.post("/stories", summary="Generate a social story")
async def story(
    principal: CurrentUser, request: Annotated[StoryRequest, Body()]
) -> dict:
    try:
        return await _client.story(
            request.job_context, request.situation, request.reading_level, request.has_trainer
        )
    except GenAiUnavailable as error:
        raise _unavailable(error) from error

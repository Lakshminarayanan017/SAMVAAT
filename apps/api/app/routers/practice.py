"""Practice loop endpoints (M4).

Two calls make the whole loop:

    POST /practice/session   -> the phrases to practise now
    POST /practice/review    -> record what happened, reschedule

Auth lands in M1; until then the user id is supplied by the caller and every
response is scoped to it. That is a development shortcut, marked as one, not a
security model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.learning.content import get_block, load_blocks
from app.learning.fsrs import Fsrs
from app.learning.grading import Attempt, derive_grade
from app.learning.repository import InMemoryCardRepository
from app.learning.session import Candidate, build_session

router = APIRouter(prefix="/practice", tags=["practice"])

# TEMPORARY: replaced by the Postgres repository in M1. Not persistent.
_repository = InMemoryCardRepository()
_fsrs = Fsrs()


# ── request / response models ────────────────────────────────────────────────


class SessionRequest(BaseModel):
    user_id: str
    session_length_target_min: int = Field(
        default=5,
        ge=2,
        le=30,
        description="The learner's preferred session length, from their profile. "
        "A target for how much to include, never a countdown (Ethics E6).",
    )
    input_mode: Literal["speech", "text", "aac", "sign", "switch"] = "text"
    one_step_per_screen: bool = False
    scenario_tags: list[str] = Field(
        default_factory=list,
        description="Optional filter, e.g. ['interview']. Empty means the whole bank.",
    )


class SessionItem(BaseModel):
    block_id: str
    canonical_text: str
    difficulty: int
    is_new: bool


class SessionResponse(BaseModel):
    items: list[SessionItem]
    estimated_seconds: int
    note: str | None = None


class ReviewRequest(BaseModel):
    user_id: str
    block_id: str
    correct: bool
    attempts: int = Field(default=1, ge=1)
    hints_used: int = Field(default=0, ge=0)
    confidence: int | None = Field(default=None, ge=1, le=5)
    low_confidence_input: bool = Field(
        default=False,
        description="True when transcription was too uncertain to trust. Never "
        "counted against the learner — an ASR weakness must not surface as theirs.",
    )
    # Deliberately absent: any timing field. See app/learning/grading.py.


class ReviewResponse(BaseModel):
    block_id: str
    grade: int
    grade_label: str
    due_at: datetime
    interval_days: float
    reps: int
    lapses: int
    #: Learner-facing, encouraging, and never a raw algorithm number.
    message: str


# ── endpoints ────────────────────────────────────────────────────────────────


@router.post("/session", response_model=SessionResponse, summary="Build a practice session")
async def create_session(request: Annotated[SessionRequest, Body()]) -> SessionResponse:
    blocks = load_blocks()

    if request.scenario_tags:
        wanted = set(request.scenario_tags)
        blocks = [b for b in blocks if wanted & set(b.get("scenario_tags", []))]

    cards = _repository.all_for_user(request.user_id)

    candidates = [
        Candidate(
            block_id=block["id"],
            card=cards.get(block["id"]),
            difficulty=block["difficulty"],
        )
        for block in blocks
    ]

    session = build_session(
        candidates,
        target_minutes=request.session_length_target_min,
        input_mode=request.input_mode,
        one_step_per_screen=request.one_step_per_screen,
    )

    items = []
    for block_id in session.items:
        block = get_block(block_id)
        if block is None:  # pragma: no cover - build/serve mismatch
            continue
        items.append(
            SessionItem(
                block_id=block_id,
                canonical_text=block["canonical_text"],
                difficulty=block["difficulty"],
                is_new=block_id not in cards,
            )
        )

    return SessionResponse(
        items=items,
        estimated_seconds=session.estimated_seconds,
        note=session.note,
    )


@router.post("/review", response_model=ReviewResponse, summary="Record a review")
async def record_review(request: Annotated[ReviewRequest, Body()]) -> ReviewResponse:
    if get_block(request.block_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown phrase '{request.block_id}'")

    grade = derive_grade(
        Attempt(
            correct=request.correct,
            attempts=request.attempts,
            hints_used=request.hints_used,
            confidence=request.confidence,
            low_confidence_input=request.low_confidence_input,
        )
    )

    now = datetime.now(timezone.utc)
    existing = _repository.get(request.user_id, request.block_id)
    card = _fsrs.review(existing, grade, now) if existing else _fsrs.new_card(grade, now)

    _repository.save(request.user_id, request.block_id, card)

    interval_days = (card.due_at - now).total_seconds() / 86_400

    return ReviewResponse(
        block_id=request.block_id,
        grade=int(grade),
        grade_label=grade.name.title(),
        due_at=card.due_at,
        interval_days=round(interval_days, 2),
        reps=card.reps,
        lapses=card.lapses,
        message=_message(grade, interval_days, request.low_confidence_input),
    )


def _message(grade, interval_days: float, low_confidence_input: bool) -> str:
    """Learner-facing feedback.

    Never says "wrong" or "failed" — the copy rules in the Ethics Charter apply
    to every string a learner reads, and this is the one they read most often.
    """
    if low_confidence_input:
        return "I was not sure what I heard, so this one does not count against you."

    if grade == 1:
        return "Not quite yet. We will come back to this one soon."
    if grade == 2:
        return "You got there. We will practise this again shortly."

    if interval_days < 2:
        return "Well done. See you again tomorrow."
    if interval_days < 14:
        return f"Well done. Next time in about {round(interval_days)} days."
    return f"You know this one well. Next time in about {round(interval_days / 7)} weeks."

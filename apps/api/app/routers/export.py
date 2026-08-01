"""Data portability (M17).

The other half of a right we already half-implemented. Erasure has been
self-service since M1; export had not been built, which left the learner able to
destroy their data but not to take it anywhere.

TWO AUDIENCES, ONE FILE
-----------------------
An export is read by two people who want opposite things. A learner wants to
know what we hold, in words. A regulator, a lawyer or the next service wants
every field. Producing only the machine version is the usual failure and it
makes the right unusable by the person it belongs to — so the payload leads
with a plain-language summary and carries the complete record underneath.

WHAT GOES IN
------------
Everything about this learner that erasure would delete. Those two lists are
the same list, and `tests/test_export.py` asserts it against the schema rather
than against a hand-written inventory — an export that omits a table we hold is
a quieter failure than an erasure that misses one, and harder to notice.

WHAT STAYS OUT
--------------
Nothing about anybody else. A trainer link names a trainer; the export says a
trainer is assigned and does not name them, because the learner's right to
their own data is not a right to someone else's identity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.tables import CardRow, TrainerLinkRow
from app.repositories.learners import (
    AuditRepository,
    ConsentRepository,
    ConversationRepository,
    ProfileRepository,
    UserRepository,
)
from app.security.auth import CurrentUser

router = APIRouter(prefix="/export", tags=["export"])

Session = Annotated[AsyncSession, Depends(get_session)]

#: Bumped when the shape changes, so a learner holding an old file can tell
#: which version they have.
EXPORT_VERSION = 1


@router.get("/me", summary="Download everything we hold about me")
async def export_me(principal: CurrentUser, session: Session) -> JSONResponse:
    user_id = principal.user_id

    user = await UserRepository(session).get(user_id)
    profiles = await ProfileRepository(session).history(user_id)
    consents = await ConsentRepository(session).history(user_id)
    conversations = await ConversationRepository(session).list_for_user(user_id)

    cards = list(
        (await session.execute(select(CardRow).where(CardRow.user_id == user_id))).scalars()
    )
    links = list(
        (
            await session.execute(
                select(TrainerLinkRow).where(TrainerLinkRow.learner_user_id == user_id)
            )
        ).scalars()
    )
    audits = await AuditRepository(session).list_for_user(user_id)

    payload: dict[str, Any] = {
        "export_version": EXPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "about_you": _plain_summary(
            profiles=profiles,
            consents=len(consents),
            cards=len(cards),
            conversations=len(conversations),
            linked=bool(links),
        ),
        "account": {
            "user_id": user_id,
            "is_guest": user.is_guest if user else True,
            "role": user.role if user else "learner",
            "created_at": _iso(getattr(user, "created_at", None)),
            "last_seen_at": _iso(getattr(user, "last_seen_at", None)),
        },
        "communication_profiles": profiles,
        "consents": [
            {
                "purpose": row.purpose,
                "granted": row.granted,
                "at": _iso(row.at),
            }
            for row in consents
        ],
        "practice": [
            {
                "block_id": card.block_id,
                "stability": card.stability,
                "difficulty": card.difficulty,
                "reps": card.reps,
                "lapses": card.lapses,
                "due_at": _iso(card.due_at),
                "last_reviewed_at": _iso(card.last_reviewed_at),
            }
            for card in cards
        ],
        "conversations": [
            {
                "id": conversation.id,
                "kind": conversation.kind,
                "finished": conversation.finished,
                "created_at": _iso(conversation.created_at),
                "exchanges": conversation.exchanges,
            }
            for conversation in conversations
        ],
        # `excluded_dimensions` is the point of including these at all: it is
        # the record of what the rubric was forbidden to grade this learner on
        # (Ethics E2), and putting it in their hands is worth more than keeping
        # it only in ours.
        "how_you_were_scored": [
            {
                "conversation_id": row.conversation_id,
                "rubric_version": row.rubric_version,
                "scored_on": row.scored_dimensions,
                "never_scored_on": row.excluded_dimensions,
                "model_id": row.model_id,
                "a_trainer_changed_this": row.trainer_override is not None,
                "reason_they_gave": row.override_reason,
                "at": _iso(row.at),
            }
            for row in audits
        ],
        # A trainer link is a fact about the learner AND about a trainer. The
        # learner is entitled to know one is assigned; the trainer's identity is
        # not the learner's data to take away.
        "support": {
            "has_a_trainer": bool(links),
            "note": (
                "A trainer is assigned to you. We do not include their name here, "
                "because this file is about you."
            )
            if links
            else "No trainer is assigned to you.",
        },
        # Named explicitly so the absence is legible rather than ambiguous.
        "audio": {
            "recordings": 0,
            "note": (
                "We do not keep recordings. Audio is deleted within 24 hours of being "
                "turned into measurements, so there is nothing here to give you."
            ),
        },
    }

    filename = f"samvaad-my-data-{datetime.now(timezone.utc):%Y-%m-%d}.json"

    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _plain_summary(
    *, profiles: list[dict], consents: int, cards: int, conversations: int, linked: bool
) -> list[str]:
    """The part a learner can actually read.

    Short sentences, no jargon, no counts presented as achievements — this is a
    record, not a progress report, and someone requesting their data is often
    doing so because they are unhappy. It should not congratulate them.
    """
    lines = [
        "This file has everything we hold about you.",
        "You can keep it, or give it to someone else.",
    ]

    if profiles:
        lines.append("It includes how you told us you prefer to communicate.")
    if consents:
        lines.append("It includes what you agreed to, and when.")
    if cards:
        lines.append(f"It includes {cards} phrases you have practised.")
    if conversations:
        lines.append(f"It includes {conversations} practice conversations.")
    if linked:
        lines.append("It says that a trainer is assigned to you.")

    lines.append("We do not keep any recordings of your voice.")
    lines.append("You can delete all of this at any time. You do not have to ask us.")
    return lines


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

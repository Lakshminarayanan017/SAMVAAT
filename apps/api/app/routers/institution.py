"""Institution analytics (M14).

The surface that lets a special school, NGO or skilling partner see whether the
programme is working — and the surface with the greatest potential to do harm,
because "anonymised cohort data" about disabled people is only anonymous if
somebody did the arithmetic properly.

THREE GATES, ALL OF THEM NECESSARY
----------------------------------
1. **Role.** Only an institution account reaches this.
2. **Consent.** A learner is counted only if they granted
   `institution_analytics` themselves. Being enrolled is not agreement.
3. **k-anonymity.** No figure derived from fewer than K learners is published,
   and neither is one whose complement is that small — otherwise the published
   figures can be subtracted from each other to recover the hidden one.

WHAT IS NEVER RETURNED
----------------------
No learner id. No name. No per-learner row, at any aggregation. There is no
parameter here that narrows the cohort, because arbitrary filtering is how
aggregate data gets turned back into individuals — ask for the intersection of
enough attributes and you have named someone.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.learning.anonymity import Cell, K, safe_percentage, suppress, suppress_breakdown
from app.models.tables import CapRow, CardRow, ConversationRow, TrainerLinkRow
from app.repositories.learners import ConsentRepository
from app.security.auth import CurrentUser

router = APIRouter(prefix="/institution", tags=["institution"])

Session = Annotated[AsyncSession, Depends(get_session)]

#: A learner counts as active if they practised within this window.
ACTIVE_WINDOW = timedelta(days=30)

#: Phrases held this long count as reliable, matching the learner-facing figure.
MASTERY_STABILITY_DAYS = 21.0


class CellOut(BaseModel):
    label: str
    count: int | None
    suppressed: bool
    reason: str = ""


class CohortReport(BaseModel):
    #: How many learners consented to be counted. Itself suppressed below K.
    learners: CellOut
    #: Everyone enrolled, consenting or not. An institution is entitled to know
    #: how many of its own learners chose not to share.
    enrolled: int
    active_last_30_days: CellOut
    completed_an_interview: CellOut
    reliable_phrases: dict[str, CellOut]
    modality_mix: dict[str, CellOut]
    #: None wherever the denominator was too small to publish a rate.
    engagement_rate: float | None
    notes: list[str]


async def _require_institution(principal: CurrentUser) -> str:
    if principal.role not in ("institution", "admin"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": "This part is for institutions.",
            },
        )
    return principal.user_id


@router.get("/cohort", response_model=CohortReport, summary="Anonymised cohort report")
async def cohort(principal: CurrentUser, session: Session) -> CohortReport:
    institution_id = await _require_institution(principal)
    consents = ConsentRepository(session)
    now = datetime.now(timezone.utc)

    # Everyone this institution has enrolled, via their trainers' caseloads.
    enrolled = [
        link.learner_user_id
        for link in (
            await session.execute(
                select(TrainerLinkRow).where(TrainerLinkRow.institution_id == institution_id)
            )
        ).scalars()
    ]
    enrolled = sorted(set(enrolled))

    # Gate 2. Enrolment is not agreement.
    counted = [
        learner
        for learner in enrolled
        if await consents.has_consent(learner, "institution_analytics")
    ]
    total = len(counted)

    notes: list[str] = []
    if len(enrolled) > total:
        notes.append(
            f"{len(enrolled) - total} of {len(enrolled)} learners have not agreed to be "
            "included in reporting. They are not counted below."
        )

    if total < K:
        notes.append(
            f"Fewer than {K} learners have agreed to be included, so no figures can be "
            "shown without risking identifying someone."
        )
        empty = CellOut(label="", count=None, suppressed=True, reason=notes[-1])
        return CohortReport(
            learners=CellOut(label="learners", count=None, suppressed=True, reason=notes[-1]),
            enrolled=len(enrolled),
            active_last_30_days=empty,
            completed_an_interview=empty,
            reliable_phrases={},
            modality_mix={},
            engagement_rate=None,
            notes=notes,
        )

    # ── the figures ──────────────────────────────────────────────────────────

    cards = list(
        (
            await session.execute(select(CardRow).where(CardRow.user_id.in_(counted)))
        ).scalars()
    )

    active = {
        card.user_id
        for card in cards
        if card.last_reviewed_at and now - card.last_reviewed_at <= ACTIVE_WINDOW
    }

    interviewed = {
        row.user_id
        for row in (
            await session.execute(
                select(ConversationRow).where(
                    ConversationRow.user_id.in_(counted),
                    ConversationRow.kind == "interview",
                    ConversationRow.finished.is_(True),
                )
            )
        ).scalars()
    }

    reliable_per_learner: dict[str, int] = {learner: 0 for learner in counted}
    for card in cards:
        if card.stability >= MASTERY_STABILITY_DAYS:
            reliable_per_learner[card.user_id] += 1

    bands = {"0-9": 0, "10-49": 0, "50+": 0}
    for count in reliable_per_learner.values():
        bands["0-9" if count < 10 else "10-49" if count < 50 else "50+"] += 1

    modality = await _modality_mix(session, counted)

    notes.append(
        f"Figures are withheld wherever fewer than {K} learners are involved, or fewer "
        f"than {K} in the remainder."
    )

    return CohortReport(
        learners=_out(suppress("learners", total, total)),
        enrolled=len(enrolled),
        active_last_30_days=_out(suppress("active", len(active), total)),
        completed_an_interview=_out(suppress("interviewed", len(interviewed), total)),
        reliable_phrases={
            label: _out(cell) for label, cell in suppress_breakdown(bands, total).items()
        },
        modality_mix={
            label: _out(cell) for label, cell in suppress_breakdown(modality, total).items()
        },
        engagement_rate=safe_percentage(len(active), total),
        notes=notes,
    )


async def _modality_mix(session: AsyncSession, learners: list[str]) -> dict[str, int]:
    """How the cohort communicates, by primary output channel.

    Useful for a centre planning staffing and equipment — and the single most
    identifying breakdown in the whole report, which is why it goes through the
    same suppression as everything else. In a centre of twelve, "1 learner uses
    Indian Sign Language" names that person to everyone who works there.
    """
    counts: dict[str, int] = {}

    for learner in learners:
        row = (
            await session.execute(
                select(CapRow)
                .where(CapRow.user_id == learner)
                .order_by(CapRow.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        channels = (row.profile or {}).get("output_channels") if row else None
        primary = channels[0] if channels else "unknown"
        counts[primary] = counts.get(primary, 0) + 1

    return counts


def _out(cell: Cell) -> CellOut:
    return CellOut(
        label=cell.label, count=cell.count, suppressed=cell.suppressed, reason=cell.reason
    )

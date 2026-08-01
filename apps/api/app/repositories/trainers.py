"""Trainer caseloads, cohort views and score overrides (M14).

THE RULE THIS MODULE EXISTS TO ENFORCE
--------------------------------------
A trainer being *responsible* for a learner and a trainer being *allowed to see
that learner's data* are two different facts, and only the second is the
learner's to give.

The link is administrative — an institution assigning a caseload. Visibility
requires the learner's own `trainer_visibility` consent. Every read of learner
data in this file passes that gate, so a trainer with a caseload of thirty sees
data only for those who chose to share it, and sees the rest as "not shared yet"
rather than as an error.

Collapsing the two would let an institution grant itself access to a disabled
person's rehearsed attempts at disclosing their disability to an employer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    CardRow,
    ConversationRow,
    RubricAuditRow,
    TrainerLinkRow,
)
from app.repositories.learners import ConsentRepository

#: A learner counts as active if they have practised within this window. Used
#: only to help a trainer prioritise, never shown to the learner as a streak or
#: a target — that would make absence a failure.
ACTIVE_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class CohortMember:
    """One learner as their trainer sees them.

    `shared` is the whole story: when it is false every metric below is None,
    because the learner has not agreed to share and we do not guess.
    """

    learner_user_id: str
    display_name: str
    shared: bool
    cards_started: int | None = None
    cards_due: int | None = None
    lapses: int | None = None
    interviews_completed: int | None = None
    last_active_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        if self.last_active_at is None:
            return False
        return datetime.now(timezone.utc) - self.last_active_at <= ACTIVE_WINDOW


class TrainerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.consents = ConsentRepository(session)

    # ── caseload ─────────────────────────────────────────────────────────────

    async def link(
        self,
        trainer_user_id: str,
        learner_user_id: str,
        display_name: str = "",
        institution_id: str | None = None,
    ) -> None:
        existing = await self.session.execute(
            select(TrainerLinkRow).where(
                TrainerLinkRow.trainer_user_id == trainer_user_id,
                TrainerLinkRow.learner_user_id == learner_user_id,
            )
        )
        row = existing.scalar_one_or_none()

        if row is None:
            self.session.add(
                TrainerLinkRow(
                    trainer_user_id=trainer_user_id,
                    learner_user_id=learner_user_id,
                    display_name=display_name,
                    institution_id=institution_id,
                )
            )
        else:
            row.display_name = display_name or row.display_name

        await self.session.flush()

    async def unlink(self, trainer_user_id: str, learner_user_id: str) -> None:
        await self.session.execute(
            delete(TrainerLinkRow).where(
                TrainerLinkRow.trainer_user_id == trainer_user_id,
                TrainerLinkRow.learner_user_id == learner_user_id,
            )
        )

    async def is_linked(self, trainer_user_id: str, learner_user_id: str) -> bool:
        result = await self.session.execute(
            select(TrainerLinkRow.id).where(
                TrainerLinkRow.trainer_user_id == trainer_user_id,
                TrainerLinkRow.learner_user_id == learner_user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def may_view(self, trainer_user_id: str, learner_user_id: str) -> bool:
        """Both facts, in order. Linked AND consented."""
        if not await self.is_linked(trainer_user_id, learner_user_id):
            return False
        return await self.consents.has_consent(learner_user_id, "trainer_visibility")

    # ── the cohort view ──────────────────────────────────────────────────────

    async def cohort(self, trainer_user_id: str) -> list[CohortMember]:
        links = (
            await self.session.execute(
                select(TrainerLinkRow)
                .where(TrainerLinkRow.trainer_user_id == trainer_user_id)
                .order_by(TrainerLinkRow.display_name, TrainerLinkRow.learner_user_id)
            )
        ).scalars()

        members: list[CohortMember] = []

        for link in links:
            shared = await self.consents.has_consent(link.learner_user_id, "trainer_visibility")

            if not shared:
                # Named, because the trainer assigned them and needs to know who
                # is on their caseload. No metrics, because the learner has not
                # agreed to share them.
                members.append(
                    CohortMember(
                        learner_user_id=link.learner_user_id,
                        display_name=link.display_name or link.learner_user_id,
                        shared=False,
                    )
                )
                continue

            members.append(await self._summarise(link))

        return members

    async def _summarise(self, link: TrainerLinkRow) -> CohortMember:
        now = datetime.now(timezone.utc)
        learner = link.learner_user_id

        cards = list(
            (
                await self.session.execute(select(CardRow).where(CardRow.user_id == learner))
            ).scalars()
        )

        interviews = (
            await self.session.execute(
                select(ConversationRow).where(
                    ConversationRow.user_id == learner,
                    ConversationRow.kind == "interview",
                    ConversationRow.finished.is_(True),
                )
            )
        ).scalars()

        reviewed = [c.last_reviewed_at for c in cards if c.last_reviewed_at]

        return CohortMember(
            learner_user_id=learner,
            display_name=link.display_name or learner,
            shared=True,
            cards_started=len(cards),
            cards_due=sum(1 for c in cards if c.due_at <= now),
            # Surfaced so a trainer can spot someone struggling, never as a
            # score. A lapse is a scheduling fact, not a judgement.
            lapses=sum(c.lapses for c in cards),
            interviews_completed=len(list(interviews)),
            last_active_at=max(reviewed) if reviewed else None,
        )

    # ── Ethics E5: overriding an AI score ────────────────────────────────────

    async def override_score(
        self,
        audit_id: str,
        trainer_user_id: str,
        override: str,
        reason: str,
    ) -> RubricAuditRow | None:
        """Record a trainer's correction of an AI score.

        Written onto the audit row rather than replacing it. The original score
        stays readable: "the AI said X, the trainer said Y, because Z" is the
        record that makes the AI answerable, and overwriting would destroy
        exactly the evidence that matters.

        Returns None when the trainer may not see this learner, so the caller
        cannot distinguish "no such record" from "not yours".
        """
        row = await self.session.get(RubricAuditRow, audit_id)
        if row is None:
            return None

        if not await self.may_view(trainer_user_id, row.user_id):
            return None

        row.trainer_override = override
        row.override_reason = reason
        await self.session.flush()
        return row

    async def override_rate(self, trainer_user_id: str) -> dict[str, int | float]:
        """How often this trainer disagrees with the AI.

        The most honest quality metric we have. A rising override rate means the
        model is drifting away from what a specialist would say, and it should
        be read before any improvement in the scores themselves.
        """
        learners = [
            link.learner_user_id
            for link in (
                await self.session.execute(
                    select(TrainerLinkRow).where(
                        TrainerLinkRow.trainer_user_id == trainer_user_id
                    )
                )
            ).scalars()
        ]

        if not learners:
            return {"scores": 0, "overridden": 0, "agreement": 1.0}

        rows = list(
            (
                await self.session.execute(
                    select(RubricAuditRow).where(RubricAuditRow.user_id.in_(learners))
                )
            ).scalars()
        )

        overridden = sum(1 for row in rows if row.trainer_override)

        return {
            "scores": len(rows),
            "overridden": overridden,
            "agreement": round(1 - overridden / len(rows), 3) if rows else 1.0,
        }

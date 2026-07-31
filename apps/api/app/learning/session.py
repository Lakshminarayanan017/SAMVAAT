"""Assembling a practice session.

The scheduler says *what is due*. This decides *what a session actually contains*,
which is a different question and a more human one.

Three constraints shape it, and all three come from the personas:

  * SESSION LENGTH is a target the learner sets, in minutes. We convert to an
    item count rather than a countdown, because a countdown is a time-pressure
    mechanic (Ethics E6). A session that runs over simply ends when the items
    end; nothing is cut off mid-answer.

  * COGNITIVE LOAD. A learner on an Easy-Read profile gets fewer items with more
    space around them. One idea per screen is not a rendering detail, it is a
    limit on how much a session may contain.

  * MORALE. At most two hard items, and always at least one the learner is
    likely to get right. A session that opens with four lapsed cards is a
    session nobody comes back from. This costs a little scheduling optimality
    and buys retention, which is the trade we want.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.learning.fsrs import CardState

#: Seconds a typical item takes end to end, per input mode.
#:
#: AAC composition and switch scanning are genuinely slower — that is the
#: modality, not the learner. Using one figure for everyone would hand an
#: AAC user a session twice as long as they asked for.
SECONDS_PER_ITEM: dict[str, int] = {
    "text": 25,
    "speech": 30,
    "aac": 55,
    "switch": 70,
    "sign": 45,
}
DEFAULT_SECONDS_PER_ITEM = 30

MAX_HARD_ITEMS = 2
#: Never build a session below this, even for a very short target — a session of
#: one item does not feel like practice.
MIN_ITEMS = 3


@dataclass(frozen=True)
class Candidate:
    """A phrase that could go into a session."""

    block_id: str
    #: None for a phrase the learner has never seen.
    card: CardState | None = None
    #: 1-5 authored difficulty, from the ContentBlock.
    difficulty: int = 3

    @property
    def is_new(self) -> bool:
        return self.card is None

    def is_due(self, now: datetime) -> bool:
        return self.card is not None and self.card.is_due(now)

    @property
    def is_hard(self) -> bool:
        """Hard for *this* learner, not hard in the abstract.

        A lapsed card or one with high FSRS difficulty is hard regardless of the
        authored level; that is the whole point of tracking difficulty per
        learner rather than per phrase.
        """
        if self.card is None:
            return self.difficulty >= 4
        return self.card.lapses > 0 or self.card.difficulty >= 7.0

    @property
    def is_likely_success(self) -> bool:
        """Comfortably known — the item we want to open a session with."""
        if self.card is None:
            return self.difficulty <= 2
        return self.card.lapses == 0 and self.card.difficulty <= 5.0 and self.card.reps >= 2


@dataclass
class Session:
    items: list[str] = field(default_factory=list)
    estimated_seconds: int = 0
    #: Populated when the session is shorter than asked for, so the UI can say
    #: why rather than looking broken.
    note: str | None = None


def item_budget(
    target_minutes: int,
    input_mode: str,
    one_step_per_screen: bool = False,
) -> int:
    """How many items fit in the learner's requested session length."""
    seconds = SECONDS_PER_ITEM.get(input_mode, DEFAULT_SECONDS_PER_ITEM)

    # One-step-per-screen profiles carry more navigation per item and, more
    # importantly, more cognitive load. Fewer items, not a faster pace.
    if one_step_per_screen:
        seconds = int(seconds * 1.5)

    return max(MIN_ITEMS, (target_minutes * 60) // seconds)


def build_session(
    candidates: list[Candidate],
    target_minutes: int,
    input_mode: str,
    one_step_per_screen: bool = False,
    now: datetime | None = None,
) -> Session:
    """Assemble a session from everything the learner could practise.

    Order of selection: due cards first (that is what spaced repetition is for),
    then new material, then review-ahead so the session is never short. The
    morale constraints are applied throughout, not bolted on at the end.
    """
    now = now or datetime.now(timezone.utc)
    budget = item_budget(target_minutes, input_mode, one_step_per_screen)

    if not candidates:
        return Session(note="Nothing to practise yet.")

    due = [c for c in candidates if c.is_due(now)]
    new = [c for c in candidates if c.is_new]
    ahead = [c for c in candidates if not c.is_due(now) and not c.is_new]

    # Most overdue first: those are closest to being forgotten.
    due.sort(key=lambda c: c.card.due_at if c.card else now)
    new.sort(key=lambda c: c.difficulty)
    ahead.sort(key=lambda c: c.card.due_at if c.card else now)

    selected: list[Candidate] = []
    hard_count = 0

    def take(pool: list[Candidate]) -> None:
        nonlocal hard_count
        for candidate in pool:
            if len(selected) >= budget:
                return
            if candidate in selected:
                continue
            if candidate.is_hard:
                if hard_count >= MAX_HARD_ITEMS:
                    continue
                hard_count += 1
            selected.append(candidate)

    take(due)
    take(new)
    take(ahead)

    # Fill any remaining budget — a learner who asked for eight minutes should
    # get eight minutes. But the hard-item cap outranks session length: topping
    # a short session up with lapsed cards defeats the exact protection the cap
    # exists for. So we exhaust the easier material first...
    remaining = [c for c in [*due, *new, *ahead] if c not in selected]

    for candidate in remaining:
        if len(selected) >= budget:
            break
        if not candidate.is_hard:
            selected.append(candidate)

    # ...and only reach for hard items if the session would otherwise be too
    # short to be worth doing at all. If everything a learner has left is hard,
    # a short session is the honest answer.
    if len(selected) < MIN_ITEMS:
        for candidate in remaining:
            if len(selected) >= MIN_ITEMS:
                break
            if candidate not in selected:
                selected.append(candidate)

    selected = _open_with_a_win(selected)

    seconds = SECONDS_PER_ITEM.get(input_mode, DEFAULT_SECONDS_PER_ITEM)
    if one_step_per_screen:
        seconds = int(seconds * 1.5)

    note = None
    if len(selected) < budget:
        note = "That is everything ready for you today. Well done."

    return Session(
        items=[c.block_id for c in selected],
        estimated_seconds=len(selected) * seconds,
        note=note,
    )


def _open_with_a_win(selected: list[Candidate]) -> list[Candidate]:
    """Move a comfortably-known item to the front, if the session has one.

    Opening on something the learner will get right is worth more than opening
    on the most overdue card. Confidence at the start of a session is what
    determines whether there is a next session.
    """
    if not selected or selected[0].is_likely_success:
        return selected

    for index, candidate in enumerate(selected):
        if candidate.is_likely_success:
            return [candidate, *selected[:index], *selected[index + 1 :]]

    return selected

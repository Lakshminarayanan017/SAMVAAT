"""k-anonymity for institution analytics (M14).

An institution wants to know whether its programme is working. It has no
business knowing which learner is which — and in a centre of six people, where
one is Deaf and one uses a switch, "anonymised" cohort figures identify
everybody unless you are careful.

THE FLOOR
---------
No figure derived from fewer than K learners is ever returned. That is the easy
half.

THE HARD HALF: DIFFERENCING
---------------------------
Suppressing small cells is not enough on its own. Given

    total learners            = 12
    learners using Easy-Read  =  9

anyone can subtract and learn that exactly 3 do not — and if a further breakdown
puts 2 of those in one category, the last one is identified by elimination.

So a cell is suppressed when EITHER the cell OR its complement falls below the
floor. That is what makes the published figures safe to subtract from each
other, and it is the check almost every "anonymised dashboard" gets wrong.

We also refuse to publish anything at all below the floor, rather than returning
zeros — a zero is a fact about a small group, and enough zeros identify people
just as well as a name does.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Below this many learners, nothing is published.
#:
#: Five is the conventional floor for small-cell suppression in education and
#: health statistics. It is not a guarantee of anonymity — nothing is — but it
#: is the point below which re-identification stops needing any effort.
K = 5

#: Shown wherever a figure has been withheld. The reason is stated, because an
#: institution that does not understand a gap assumes a bug and asks us to
#: remove the protection.
SUPPRESSED_NOTE = (
    f"Withheld: fewer than {K} learners, or fewer than {K} in the remainder. "
    "Publishing it could identify someone."
)


@dataclass(frozen=True)
class Cell:
    """One published figure, or a refusal to publish one."""

    label: str
    #: None when suppressed. Never zero-as-a-stand-in — a zero is itself a fact
    #: about a small group.
    count: int | None
    suppressed: bool = False
    reason: str = ""

    @property
    def published(self) -> bool:
        return self.count is not None


def suppress(label: str, count: int, total: int) -> Cell:
    """Publish a count, or refuse to.

    Suppressed when the cell is small OR its complement is — otherwise the two
    published figures can be subtracted to recover the small one.
    """
    complement = total - count

    if total < K:
        return Cell(label, None, True, f"The whole group is smaller than {K}.")

    if count < K:
        return Cell(label, None, True, SUPPRESSED_NOTE)

    if 0 < complement < K:
        # The cell itself is large, but everyone NOT in it is a group of one or
        # two — and `total - count` reveals exactly how many.
        return Cell(label, None, True, SUPPRESSED_NOTE)

    return Cell(label, count)


def suppress_breakdown(counts: dict[str, int], total: int) -> dict[str, Cell]:
    """Apply the floor across a whole breakdown.

    Categories are suppressed together rather than one at a time: if only one
    category in a breakdown were withheld, its value would be recoverable by
    subtracting the others from the total. So once any category is suppressed,
    the smallest surviving one goes too, until nothing is recoverable.
    """
    cells = {label: suppress(label, count, total) for label, count in counts.items()}

    if total < K:
        return cells

    # Recoverable-by-subtraction check. Repeat until stable: removing one
    # category can make the next one recoverable in turn.
    while True:
        published = {label: cell for label, cell in cells.items() if cell.published}
        suppressed_count = sum(
            counts[label] for label, cell in cells.items() if not cell.published
        )

        # If exactly one category is hidden, its size is total minus the rest.
        hidden = [label for label, cell in cells.items() if not cell.published]
        recoverable = len(hidden) == 1 and suppressed_count > 0

        if not recoverable or not published:
            return cells

        # Hide the smallest published category too, so the hidden total covers
        # at least two categories and no single value can be recovered.
        smallest = min(published, key=lambda label: counts[label])
        cells[smallest] = Cell(smallest, None, True, SUPPRESSED_NOTE)


def safe_percentage(count: int, total: int) -> float | None:
    """A proportion, or nothing.

    A percentage over a small denominator is a count wearing a disguise: 1 of 3
    is "33%", and anyone who knows the denominator has the count back.
    """
    if total < K or count < K or 0 < total - count < K:
        return None
    return round(100 * count / total, 1)

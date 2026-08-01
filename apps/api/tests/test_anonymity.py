"""k-anonymity.

Suppressing small cells is the easy half and the half everyone does. These tests
are mostly about the other half: whether the figures we DO publish can be
subtracted from each other to recover the ones we withheld.

In a centre of twelve where one learner uses Indian Sign Language, getting this
wrong names that person to everyone who works there.
"""

from __future__ import annotations

from app.learning.anonymity import K, safe_percentage, suppress, suppress_breakdown


class TestTheFloor:
    def test_a_small_cell_is_withheld(self) -> None:
        assert suppress("deaf", K - 1, 100).suppressed is True

    def test_a_large_cell_is_published(self) -> None:
        cell = suppress("typing", 40, 100)
        assert cell.published is True
        assert cell.count == 40

    def test_nothing_is_published_when_the_whole_group_is_small(self) -> None:
        assert suppress("anything", 2, K - 1).suppressed is True

    def test_a_withheld_cell_carries_no_number_at_all(self) -> None:
        """Not zero-as-a-stand-in. A zero is itself a fact about a small group,
        and enough zeros identify people as well as a name does."""
        cell = suppress("deaf", 1, 100)
        assert cell.count is None

    def test_a_withheld_cell_explains_itself(self) -> None:
        """An institution that does not understand a gap assumes a bug and asks
        us to remove the protection."""
        assert "identify someone" in suppress("deaf", 1, 100).reason.lower()

    def test_exactly_k_is_published(self) -> None:
        assert suppress("group", K, 100).published is True


class TestDifferencing:
    """The half that is usually got wrong."""

    def test_a_cell_whose_complement_is_small_is_also_withheld(self) -> None:
        """total 12, cell 10 -> everyone NOT in it is a group of two, and
        `total - count` reveals exactly how many."""
        assert suppress("uses_text", 10, 12).suppressed is True

    def test_a_full_cell_is_publishable(self) -> None:
        """A complement of zero identifies nobody: "all 20 use text" says
        nothing about any individual that the others do not also say."""
        assert suppress("uses_text", 20, 20).published is True

    def test_one_hidden_category_is_never_left_recoverable(self) -> None:
        """If only one category in a breakdown is withheld, its size is the
        total minus the published rest. So a second one goes too."""
        cells = suppress_breakdown({"text": 30, "audio": 25, "isl": 2}, total=57)

        hidden = [label for label, cell in cells.items() if not cell.published]
        assert len(hidden) >= 2, f"only {hidden} withheld — its size is recoverable"

    def test_the_second_suppression_takes_the_smallest_survivor(self) -> None:
        """Hiding the largest category would destroy most of the report's value
        for no extra protection."""
        cells = suppress_breakdown({"text": 40, "audio": 12, "isl": 2}, total=54)

        assert cells["text"].published is True
        assert cells["audio"].published is False
        assert cells["isl"].published is False

    def test_a_breakdown_with_two_small_categories_needs_no_extra_hiding(self) -> None:
        cells = suppress_breakdown({"text": 30, "audio": 3, "isl": 2}, total=35)

        published = [label for label, cell in cells.items() if cell.published]
        assert published == ["text"]

    def test_published_categories_never_sum_to_reveal_a_hidden_one(self) -> None:
        """The property the whole module exists for, checked directly."""
        for breakdown, total in [
            ({"a": 30, "b": 25, "c": 2}, 57),
            ({"a": 10, "b": 9, "c": 8, "d": 1}, 28),
            ({"a": 50, "b": 4}, 54),
            ({"a": 6, "b": 6, "c": 6, "d": 3}, 21),
        ]:
            cells = suppress_breakdown(breakdown, total)
            published = sum(
                breakdown[label] for label, cell in cells.items() if cell.published
            )
            hidden_total = total - published
            hidden_labels = [label for label, cell in cells.items() if not cell.published]

            if hidden_labels:
                # Either nothing is hidden, or what is hidden covers at least
                # two categories so no single value can be recovered.
                assert len(hidden_labels) >= 2 or hidden_total == 0, (
                    f"{breakdown}: {hidden_labels} recoverable as {hidden_total}"
                )

    def test_a_breakdown_of_a_small_cohort_publishes_nothing(self) -> None:
        cells = suppress_breakdown({"text": 2, "audio": 1}, total=3)
        assert all(not cell.published for cell in cells.values())


class TestPercentages:
    def test_a_percentage_over_a_small_denominator_is_withheld(self) -> None:
        """1 of 3 is "33%", and anyone who knows the denominator has the count
        back. A percentage is a count wearing a disguise."""
        assert safe_percentage(1, 3) is None

    def test_a_percentage_of_a_small_numerator_is_withheld(self) -> None:
        assert safe_percentage(2, 100) is None

    def test_a_percentage_whose_complement_is_small_is_withheld(self) -> None:
        assert safe_percentage(98, 100) is None

    def test_an_ordinary_percentage_is_published(self) -> None:
        assert safe_percentage(40, 100) == 40.0

    def test_a_full_percentage_is_publishable(self) -> None:
        assert safe_percentage(20, 20) == 100.0

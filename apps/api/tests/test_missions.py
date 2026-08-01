"""Mission generation.

The load-bearing test is `TestTheFiveProperties`, which runs every mission the
generator can produce, of every type, against the five rules in Blueprint §7.4.
A sixth mission type added without those properties fails there rather than in a
learner's session.

Everything else here is about the refusals: that a profile weight biases the mix
and never removes a type, that no mission can be built without a scaffold, and
that no learner-facing string tells somebody they are wrong.
"""

from __future__ import annotations

import pytest

from app.learning.missions import (
    IMPLEMENTED,
    MAX_MISSIONS,
    MIN_MISSIONS,
    build_missions,
)


def phrases(count: int = 6) -> list[dict]:
    return [
        {"block_id": f"phrase.greetings.p{i:02d}", "canonical_text": f"Phrase number {i}"}
        for i in range(count)
    ]


class TestTheFiveProperties:
    """Blueprint §7.4, checked against every type the generator can produce."""

    @pytest.fixture
    def every_mission(self):
        missions = []
        for mission_type in sorted(IMPLEMENTED):
            plan = build_missions("lvl", [mission_type], phrases(), seed="s")
            missions.extend(plan.missions)
        assert missions, "generator produced nothing — the suite would pass vacuously"
        return missions

    def test_every_mission_offers_a_scaffold(self, every_mission) -> None:
        """A mission with no way to ask for help is a mission a learner can get
        stuck in, and getting stuck with no exit is how somebody decides the app
        is not for them."""
        for mission in every_mission:
            assert mission.scaffold, f"{mission.type} has no scaffold"

    def test_no_mission_mentions_time(self, every_mission) -> None:
        """Ethics E6. Not a countdown, not a bonus, not a "you took a while"."""
        banned = ("second", "timer", "countdown", "quickly", "fast", "hurry", "time left")
        for mission in every_mission:
            text = " ".join([mission.prompt, mission.scaffold, mission.coaching]).lower()
            for word in banned:
                assert word not in text, f"{mission.type} mentions {word!r}"

    def test_no_mission_tells_the_learner_they_are_wrong(self, every_mission) -> None:
        """Coaching, never a verdict. This is the sentence a learner reads on
        the day they are already having a bad time."""
        for mission in every_mission:
            lowered = mission.coaching.lower()
            assert "wrong" not in lowered
            assert "incorrect" not in lowered
            assert "failed" not in lowered

    def test_coaching_says_what_does_fit(self, every_mission) -> None:
        """"Not quite" on its own leaves the learner exactly where they were."""
        for mission in every_mission:
            assert mission.answer_text in mission.coaching

    def test_every_mission_names_a_real_block(self, every_mission) -> None:
        """The block id is what routes the mission through the modality router.
        A mission without one cannot be rendered in five channels."""
        for mission in every_mission:
            assert mission.block_id


class TestChoiceMissions:
    def test_distractors_come_from_the_same_level(self) -> None:
        """A distractor from a different world is obviously wrong and teaches
        nothing. One from the same chapter is a phrase the learner is also
        learning, so choosing between them is the actual skill."""
        pool = phrases()
        plan = build_missions("lvl", ["recognise"], pool, seed="s")
        texts = {p["canonical_text"] for p in pool}

        for mission in plan.missions:
            for option in mission.options:
                assert option in texts

    def test_the_answer_is_always_among_the_options(self) -> None:
        plan = build_missions("lvl", ["recognise"], phrases(), seed="s")
        for mission in plan.missions:
            assert mission.answer_text in mission.options

    def test_options_are_not_always_in_the_same_position(self) -> None:
        """An answer that is always first is a pattern a learner will find
        before they find the phrase."""
        plan = build_missions("lvl", ["recognise"], phrases(12), seed="mix")
        positions = {m.options.index(m.answer_text) for m in plan.missions if m.options}
        assert len(positions) > 1, "the answer is always in the same slot"

    def test_a_level_too_small_for_choices_falls_back_to_production(self) -> None:
        """A choice mission with one option is not a choice. Better a different
        mission than a single button presented as a question."""
        plan = build_missions("lvl", ["recognise"], phrases(1), seed="s")
        for mission in plan.missions:
            assert mission.options == () or len(mission.options) >= 2


class TestProfileWeights:
    def test_weights_bias_the_mix(self) -> None:
        heavy = build_missions(
            "lvl",
            ["recognise", "produce"],
            phrases(6),
            weights={"recognise": 10.0, "produce": 0.1},
            seed="w",
        )
        counts = [m.type for m in heavy.missions]
        assert counts.count("recognise") > counts.count("produce")

    def test_a_zero_weight_still_leaves_a_type_reachable(self) -> None:
        """Bias, never elimination. A weight of zero would remove a kind of
        practice from a learner's experience because of their disability, which
        is the exact harm this product exists to refuse (§12.3)."""
        seen: set[str] = set()
        for attempt in range(60):
            plan = build_missions(
                "lvl",
                ["recognise", "produce"],
                phrases(6),
                weights={"recognise": 1.0, "produce": 0.0},
                seed=f"seed-{attempt}",
            )
            seen.update(m.type for m in plan.missions)

        assert "produce" in seen, "a zero weight removed the type entirely"

    def test_no_weights_still_produces_a_valid_plan(self) -> None:
        plan = build_missions("lvl", ["recognise"], phrases(), seed="s")
        assert plan.total >= MIN_MISSIONS


class TestPlanShape:
    def test_a_plan_is_short_enough_that_the_end_is_visible(self) -> None:
        """The blueprint targets 3-7 minutes with a visible end. Past about six
        missions the end stops being visible, which is the mechanic the whole
        loop depends on."""
        plan = build_missions("lvl", ["recognise"], phrases(50), seed="s")
        assert MIN_MISSIONS <= plan.total <= MAX_MISSIONS

    def test_a_short_level_is_not_padded_by_repeating_a_phrase(self) -> None:
        plan = build_missions("lvl", ["recognise"], phrases(2), seed="s")
        block_ids = [m.block_id for m in plan.missions]
        assert len(block_ids) == len(set(block_ids))

    def test_the_same_learner_reopening_a_level_gets_the_same_plan(self) -> None:
        """Reopening a level mid-session must not reshuffle it into different
        missions — the learner would reasonably conclude their progress was
        lost."""
        a = build_missions("lvl", ["recognise", "produce"], phrases(), seed="learner-1")
        b = build_missions("lvl", ["recognise", "produce"], phrases(), seed="learner-1")

        assert [m.id for m in a.missions] == [m.id for m in b.missions]
        assert [m.type for m in a.missions] == [m.type for m in b.missions]
        assert [m.options for m in a.missions] == [m.options for m in b.missions]

    def test_two_learners_get_different_orders(self) -> None:
        a = build_missions("lvl", ["recognise"], phrases(8), seed="learner-1")
        b = build_missions("lvl", ["recognise"], phrases(8), seed="learner-2")
        assert [m.options for m in a.missions] != [m.options for m in b.missions]

    def test_mission_ids_are_unique_within_a_level(self) -> None:
        plan = build_missions("lvl", ["recognise"], phrases(), seed="s")
        ids = [m.id for m in plan.missions]
        assert len(ids) == len(set(ids))


class TestUnimplementedTypes:
    def test_a_level_declaring_only_unbuilt_types_still_runs(self) -> None:
        """A learner must never meet an empty level because a mission type is
        unfinished. The curriculum names eight types; three are built."""
        plan = build_missions("lvl", ["roleplay", "boss", "interview"], phrases(), seed="s")

        assert plan.total >= MIN_MISSIONS
        assert all(m.type in IMPLEMENTED for m in plan.missions)

    def test_declared_types_that_are_built_are_preferred_over_the_fallback(self) -> None:
        plan = build_missions("lvl", ["produce", "roleplay"], phrases(), seed="s")
        assert all(m.type == "produce" for m in plan.missions)

    def test_an_empty_declaration_still_runs(self) -> None:
        plan = build_missions("lvl", [], phrases(), seed="s")
        assert plan.total >= MIN_MISSIONS

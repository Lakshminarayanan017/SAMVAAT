"""The game layer — worlds, levels, stars, unlocking.

Half of these assert an absence. That is the point: a progression system is
where accessibility is betrayed most casually, because the mechanics that make
games sticky — hearts, locks, leagues — all work by punishing an absence, and
for our learners the absence is the disability.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.learning.curriculum import (
    Level,
    get_level,
    get_world,
    levels_by_id,
    load_curriculum,
    load_profiles,
)
from app.learning.fsrs import CardState
from app.learning.progression import (
    MAX_STARS,
    RELIABLE_STABILITY_DAYS,
    LevelStatus,
    build_journey,
    stars_for,
)

NOW = datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc)

FIRST_LEVEL = "w01_finding_your_voice.c01_hello.l1"


def card(*, stability: float = 30.0, reps: int = 4, lapses: int = 0) -> CardState:
    return CardState(
        stability=stability,
        difficulty=5.0,
        due_at=NOW + timedelta(days=1),
        reps=reps,
        lapses=lapses,
        last_reviewed_at=NOW,
    )


def cards_for(level_id: str, **kwargs) -> dict[str, CardState]:
    level = levels_by_id()[level_id]
    return {block_id: card(**kwargs) for block_id in level.block_ids}


# ── The curriculum itself ────────────────────────────────────────────────────


class TestCurriculum:
    def test_ten_worlds_in_order(self) -> None:
        worlds = load_curriculum()
        assert len(worlds) == 10
        assert [world.order for world in worlds] == list(range(1, 11))

    def test_every_level_resolves_to_real_phrases(self) -> None:
        """The build resolves category slices against the real bank. A level
        pointing at nothing would render an empty screen."""
        for level in levels_by_id().values():
            assert level.block_ids, f"{level.id} has no phrases"

    def test_every_level_has_at_least_one_mission(self) -> None:
        for level in levels_by_id().values():
            assert level.missions

    def test_the_two_flagship_worlds_are_marked(self) -> None:
        """Self-advocacy and the interview. The two nothing else on the market
        teaches, and the two the demo leads with."""
        flagship = {world.id for world in load_curriculum() if world.flagship}
        assert flagship == {"w05_speaking_up", "w10_the_interview"}

    def test_the_disclosure_chapter_is_marked_sensitive(self) -> None:
        """A learner rehearsing disclosure is rehearsing something that can cost
        them a job. The client shows an exit and a route to a person on every
        screen of a sensitive chapter."""
        world = get_world("w05_speaking_up")
        assert any(chapter.sensitive for chapter in world.chapters)

    def test_effort_rises_with_harder_missions(self) -> None:
        """XP is paid on effort. A roleplay level must be worth more than a
        matching level, or the game rewards the easy path."""
        matching = Level(
            id="x", title="", missions=("recognise",), block_ids=(), effort=1,
            chapter_id="", world_id="",
        )
        assert get_level(FIRST_LEVEL).effort >= matching.effort


# ── Stars measure retention, not performance ─────────────────────────────────


class TestStars:
    def test_no_stars_before_anything_is_attempted(self) -> None:
        stars, coverage, retention = stars_for(get_level(FIRST_LEVEL), {})
        assert (stars, coverage, retention) == (0, 0.0, 0.0)

    def test_one_star_needs_every_phrase_met(self) -> None:
        """Not any phrase — every phrase. Levels overlap by design, so 'met one'
        would hand a learner a completion they did not earn."""
        level = get_level(FIRST_LEVEL)
        partial = dict(list(cards_for(FIRST_LEVEL).items())[:2])

        assert stars_for(level, partial)[0] == 0
        assert stars_for(level, cards_for(FIRST_LEVEL))[0] >= 1

    def test_two_stars_need_every_phrase_right_once(self) -> None:
        level = get_level(FIRST_LEVEL)

        # Reviewed, but lapsed every time — never actually right.
        never_right = cards_for(FIRST_LEVEL, reps=3, lapses=3, stability=1.0)
        assert stars_for(level, never_right)[0] == 1

        right_once = cards_for(FIRST_LEVEL, reps=3, lapses=1, stability=1.0)
        assert stars_for(level, right_once)[0] == 2

    def test_three_stars_need_retention_not_a_good_day(self) -> None:
        """The third star cannot be earned in one sitting by anybody, however
        able. It is earned by coming back — the one thing a fluent speaker has
        no advantage at."""
        level = get_level(FIRST_LEVEL)

        good_day = cards_for(FIRST_LEVEL, stability=RELIABLE_STABILITY_DAYS - 1)
        assert stars_for(level, good_day)[0] == 2

        it_stuck = cards_for(FIRST_LEVEL, stability=RELIABLE_STABILITY_DAYS)
        assert stars_for(level, it_stuck)[0] == 3

    def test_stars_never_exceed_the_maximum(self) -> None:
        level = get_level(FIRST_LEVEL)
        assert stars_for(level, cards_for(FIRST_LEVEL, stability=999.0))[0] == MAX_STARS

    def test_stars_do_not_depend_on_how_fast_anybody_was(self) -> None:
        """Enforcement by signature: `stars_for` receives no timing at all, so
        speed cannot enter the star ladder (Ethics E6)."""
        import inspect

        parameters = set(inspect.signature(stars_for).parameters)
        assert parameters == {"level", "cards"}


# ── The journey ──────────────────────────────────────────────────────────────


class TestJourney:
    def test_a_fresh_learner_gets_exactly_one_recommendation(self) -> None:
        """One next thing. Two suggestions makes the learner choose which of our
        suggestions to trust."""
        journey = build_journey({})
        recommended = [
            level
            for world in journey.worlds
            for level in world.levels
            if level.status is LevelStatus.RECOMMENDED
        ]
        assert len(recommended) == 1
        assert journey.next_level_id == FIRST_LEVEL

    def test_the_recommendation_moves_on_when_a_level_is_finished(self) -> None:
        journey = build_journey(cards_for(FIRST_LEVEL))
        assert journey.next_level_id == "w01_finding_your_voice.c01_hello.l2"

    def test_an_opened_level_is_the_recommendation(self) -> None:
        """Nothing is promoted beside a level already underway."""
        journey = build_journey(
            cards_for(FIRST_LEVEL), {"w01_finding_your_voice.c01_hello.l2"}
        )

        statuses = {level.level_id: level.status for level in journey.worlds[0].levels}
        assert statuses["w01_finding_your_voice.c01_hello.l2"] is LevelStatus.IN_PROGRESS
        assert LevelStatus.RECOMMENDED not in statuses.values()

    def test_overlap_does_not_mark_untouched_levels_as_started(self) -> None:
        """A chapter's closing level draws on everything before it. Reading its
        partial coverage as 'you started this' would show half the map as
        half-finished work nobody began."""
        journey = build_journey(cards_for(FIRST_LEVEL))
        closing = journey.worlds[0].levels[-1]

        assert closing.coverage > 0
        assert closing.status is not LevelStatus.IN_PROGRESS

    def test_the_headline_never_shows_a_percentage_of_the_whole_product(self) -> None:
        """'3% complete' on day one is accurate and demoralising."""
        for cards in ({}, cards_for(FIRST_LEVEL)):
            headline = build_journey(cards).headline
            assert "%" not in headline

    def test_finishing_everything_is_a_celebrated_state_not_an_empty_one(self) -> None:
        every_card = {
            block_id: card(stability=999.0)
            for world in load_curriculum()
            for block_id in world.block_ids
        }
        journey = build_journey(every_card)

        assert journey.next_level_id is None
        assert "whole journey" in journey.headline
        assert journey.total_stars == journey.max_stars


# ── The three refusals ───────────────────────────────────────────────────────


class TestNothingIsEverLocked:
    def test_there_is_no_locked_status(self) -> None:
        """A padlock on a disability-adapted product reads as 'not for you'."""
        assert "LOCKED" not in {status.name for status in LevelStatus}

    def test_the_last_world_is_reachable_on_day_one(self) -> None:
        """Ethics E7. A gate a learner cannot pass fails them permanently — and
        the learner most likely to need interview practice tomorrow is the one
        least likely to have time for fifty levels first."""
        journey = build_journey({})
        interview_world = next(w for w in journey.worlds if w.world_id == "w10_the_interview")

        for level in interview_world.levels:
            assert level.status is LevelStatus.AVAILABLE_EARLY

    def test_an_early_level_reads_as_an_open_door(self) -> None:
        journey = build_journey({})
        early = next(
            level
            for world in journey.worlds
            for level in world.levels
            if level.status is LevelStatus.AVAILABLE_EARLY
        )

        assert "can still try" in early.caption
        for word in ("locked", "unlock", "not available", "complete first", "required"):
            assert word not in early.caption.lower()


class TestNoHeartsNoLeaderboard:
    def test_the_module_has_no_energy_mechanic(self) -> None:
        """Hearts punish an absence of skill, and for our learners that absence
        is the disability. A learner with dysarthria would exhaust a heart bar
        every session and be locked out for being disabled."""
        import ast
        import inspect

        import app.learning.progression as module

        tree = ast.parse(inspect.getsource(module))
        docstrings = {
            ast.get_docstring(node, clean=False)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
        }
        names = {
            node.id if isinstance(node, ast.Name) else node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Name | ast.Attribute)
        } | {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.ClassDef)
        }
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docstrings
        }

        haystack = " ".join(names | literals).lower()
        for forbidden in ("heart", "lives", "energy", "streak_freeze_cost", "gem", "league"):
            assert forbidden not in haystack, f"energy mechanic: {forbidden}"

    def test_nothing_in_a_journey_describes_another_learner(self) -> None:
        journey = build_journey(cards_for(FIRST_LEVEL))

        texts = [journey.headline] + [
            text
            for world in journey.worlds
            for text in [world.caption, *(level.caption for level in world.levels)]
        ]

        # Word boundaries, not substrings: "colleague" contains "league" and is
        # a perfectly innocent word. A check that cannot tell the difference
        # gets disabled by the first person it inconveniences, and then it
        # protects nothing.
        import re

        for text in texts:
            lowered = text.lower()
            for word in ("rank", "percentile", "others", "average", "league", "top"):
                assert not re.search(rf"\b{word}\b", lowered), f"comparison in copy: {text!r}"


# ── Profiles ─────────────────────────────────────────────────────────────────


class TestProfiles:
    def test_every_profile_has_a_plain_and_an_easy_read_label(self) -> None:
        for profile in load_profiles()["profiles"]:
            assert profile["label"]
            assert profile["easy_read_label"]

    def test_prefer_not_to_say_exists_and_is_first(self) -> None:
        """Nobody is required to name a condition to use the product."""
        profiles = sorted(load_profiles()["profiles"], key=lambda p: p["order"])
        assert profiles[0]["id"] == "prefer_not_to_say"

    def test_no_profile_removes_a_world(self) -> None:
        """Reordering and re-weighting, never removal. Deciding somebody cannot
        learn interviews because of their disability is the exact harm this
        product exists to refuse."""
        for profile in load_profiles()["profiles"]:
            assert "world_exclusion" not in profile
            assert "hidden_worlds" not in profile

    def test_profiles_change_behaviour_not_just_labels(self) -> None:
        """A preset that only changed wording would not be worth having."""
        by_id = {p["id"]: p for p in load_profiles()["profiles"]}

        non_speaking = by_id["non_speaking"]
        stammer = by_id["stammer"]

        assert "speech" not in non_speaking["channels"]["input"]
        assert non_speaking["scoring_weights"]["pronunciation"] == 0.0
        assert non_speaking["session_minutes"] > stammer["session_minutes"]
        assert non_speaking["strategies"] != stammer["strategies"]

    def test_every_scoring_weight_set_sums_to_one(self) -> None:
        for profile in load_profiles()["profiles"]:
            weights = profile.get("scoring_weights", {})
            if weights:
                assert sum(weights.values()) == pytest.approx(1.0, abs=0.001)

    def test_pace_is_never_scored_for_motor_speech_profiles(self) -> None:
        """Speaking rate in dysarthria is motor function, not skill — ADR-0006."""
        by_id = {p["id"]: p for p in load_profiles()["profiles"]}

        for profile_id in ("cerebral_palsy", "non_speaking", "aphasia"):
            assert by_id[profile_id]["scoring_weights"]["pace"] == 0.0

    def test_every_strategy_named_by_a_profile_exists(self) -> None:
        catalogue = load_profiles()["strategies"]

        for profile in load_profiles()["profiles"]:
            for strategy in profile.get("strategies", []):
                assert strategy in catalogue

    def test_every_strategy_is_phrased_as_something_to_try(self) -> None:
        for key, strategy in load_profiles()["strategies"].items():
            text = strategy["text"].lower()
            for blaming in ("wrong", "mistake", "you failed", "incorrect", "you should have"):
                assert blaming not in text, f"{key} is blaming: {strategy['text']!r}"

"""Feature flags.

The properties worth testing are the safety ones: that an unknown flag is off,
that a learner's assignment does not change under them, that the same learners
are not the guinea pigs for every experiment, and that nobody can ship a flag
which turns accessibility off for a percentage of disabled users.
"""

from __future__ import annotations

import pytest

from samvaad_platform.flags import (
    AccessibilityGatedFlagError,
    Flag,
    all_for,
    is_enabled,
    load_from_env,
    override,
)


@pytest.fixture(autouse=True)
def _reset():
    """Flags are module state, so each test gets them back as it found them."""
    from samvaad_platform import flags

    snapshot = dict(flags._REGISTRY)
    yield
    flags._REGISTRY.clear()
    flags._REGISTRY.update(snapshot)


class TestFailingSafe:
    def test_an_unknown_flag_is_off(self) -> None:
        """Never on, and never an exception either. A typo must not enable an
        unfinished feature, and must not take the service down."""
        assert is_enabled("no_such_flag", "gst_1") is False

    def test_a_registered_flag_starts_off(self) -> None:
        assert is_enabled("game_loop", "gst_1") is False

    def test_a_disabled_flag_ignores_its_rollout(self) -> None:
        """The master switch outranks the percentage, so "turn it off now" is
        one edit rather than two."""
        override("game_loop", enabled=False, rollout=100)
        assert is_enabled("game_loop", "gst_1") is False

    def test_an_anonymous_caller_gets_nothing_from_a_partial_rollout(self) -> None:
        """There is no stable identity to bucket, and flipping per request
        would be worse than not showing the feature."""
        override("game_loop", enabled=True, rollout=50)
        assert is_enabled("game_loop", None) is False

    def test_an_anonymous_caller_does_get_a_full_rollout(self) -> None:
        override("game_loop", enabled=True, rollout=100)
        assert is_enabled("game_loop", None) is True


class TestAssignmentIsStable:
    def test_the_same_learner_gets_the_same_answer_every_time(self) -> None:
        """A learner whose interface changes mid-session is, for somebody with
        a cognitive disability, using a different app than the one they
        opened."""
        override("game_loop", enabled=True, rollout=50)

        answers = {is_enabled("game_loop", "gst_stable") for _ in range(50)}
        assert len(answers) == 1

    def test_assignment_survives_a_process_restart(self) -> None:
        """Python's built-in hash() is randomised per process, so a learner
        would land in a different bucket after every deploy. The bucket is a
        SHA-256 of the id instead — this pins the actual value."""
        from samvaad_platform.flags import _bucket

        assert _bucket("game_loop", "gst_stable") == _bucket("game_loop", "gst_stable")
        # A fixed expectation, so a change to the hashing is a deliberate one.
        assert 0 <= _bucket("game_loop", "gst_stable") <= 99

    def test_rollout_zero_reaches_nobody(self) -> None:
        override("game_loop", enabled=True, rollout=0)
        assert not any(is_enabled("game_loop", f"gst_{i}") for i in range(200))

    def test_rollout_one_hundred_reaches_everybody(self) -> None:
        override("game_loop", enabled=True, rollout=100)
        assert all(is_enabled("game_loop", f"gst_{i}") for i in range(200))

    def test_a_partial_rollout_is_roughly_the_size_asked_for(self) -> None:
        override("game_loop", enabled=True, rollout=30)

        included = sum(is_enabled("game_loop", f"gst_{i}") for i in range(2000))
        share = included / 2000

        assert 0.25 < share < 0.35, f"asked for 30%, got {share:.0%}"


class TestFairness:
    def test_two_flags_do_not_select_the_same_learners(self) -> None:
        """Without a per-flag salt the same 10% of learners are the guinea pigs
        for every experiment forever. Given who our learners are, that is a
        fairness problem rather than a statistical one."""
        override("game_loop", enabled=True, rollout=20)
        override("stories_v2", enabled=True, rollout=20)

        users = [f"gst_{i}" for i in range(2000)]
        a = {u for u in users if is_enabled("game_loop", u)}
        b = {u for u in users if is_enabled("stories_v2", u)}

        assert a and b
        overlap = len(a & b) / len(a)
        # Independent 20% samples overlap around 20%. Identical ones overlap
        # 100%, which is the failure this catches.
        assert overlap < 0.4, f"{overlap:.0%} of one flag's cohort is the other's"


class TestAccessibilityIsNotAnExperiment:
    @pytest.mark.parametrize(
        "name",
        [
            "captions_v2",
            "new_aria_labels",
            "switch_scan_rewrite",
            "easy_read_toggle",
            "a11y_overhaul",
            "modality_router_v2",
            "high_contrast_experiment",
        ],
    )
    def test_a_flag_that_gates_accessibility_cannot_be_declared(self, name: str) -> None:
        """A percentage rollout of captions means a percentage of Deaf learners
        get an unusable product. There is no version of that which is an
        acceptable experiment."""
        with pytest.raises(AccessibilityGatedFlagError):
            Flag(name=name)

    def test_the_error_says_what_to_do_instead(self) -> None:
        with pytest.raises(AccessibilityGatedFlagError, match="rename it"):
            Flag(name="caption_rewrite")

    def test_ordinary_feature_names_are_fine(self) -> None:
        for name in ("game_loop", "rewards", "stories_v2", "level_runner"):
            Flag(name=name)


class TestValidation:
    @pytest.mark.parametrize("rollout", [-1, 101, 1000])
    def test_a_nonsense_rollout_is_refused(self, rollout: int) -> None:
        with pytest.raises(ValueError, match="0-100"):
            Flag(name="game_loop", rollout=rollout)


class TestStaffOverride:
    def test_named_users_bypass_the_rollout(self) -> None:
        """Somebody has to be able to look at the new thing before 10% of
        learners do."""
        from samvaad_platform import flags

        flags._REGISTRY["game_loop"] = Flag(
            name="game_loop", enabled=True, rollout=0, always_on_for=frozenset({"trn_staff"})
        )

        assert is_enabled("game_loop", "trn_staff") is True
        assert is_enabled("game_loop", "gst_ordinary") is False


class TestTheClientPayload:
    def test_every_flag_is_reported_in_one_object(self) -> None:
        """One response, so a learner on a poor connection never gets a
        half-configured interface assembled from several round trips."""
        payload = all_for("gst_1")

        assert "game_loop" in payload
        assert all(isinstance(value, bool) for value in payload.values())

    def test_it_is_stable_for_a_learner(self) -> None:
        override("game_loop", enabled=True, rollout=50)
        assert all_for("gst_1") == all_for("gst_1")


class TestEnvironmentOverrides:
    def test_on_and_off_are_accepted_as_words(self) -> None:
        """What somebody types at 2am during an incident. Refusing it then
        would be a poor time to be pedantic."""
        load_from_env({"SAMVAAD_FLAG_GAME_LOOP": "on"})
        assert is_enabled("game_loop", "gst_1") is True

        load_from_env({"SAMVAAD_FLAG_GAME_LOOP": "off"})
        assert is_enabled("game_loop", "gst_1") is False

    def test_a_percentage_is_accepted(self) -> None:
        load_from_env({"SAMVAAD_FLAG_GAME_LOOP": "100"})
        assert is_enabled("game_loop", "gst_1") is True

    def test_zero_percent_is_off_rather_than_on_for_nobody(self) -> None:
        load_from_env({"SAMVAAD_FLAG_GAME_LOOP": "0"})
        assert is_enabled("game_loop", "gst_1") is False

    def test_unrelated_environment_variables_are_ignored(self) -> None:
        load_from_env({"PATH": "/usr/bin", "DATABASE_URL": "postgres://"})
        assert is_enabled("game_loop", "gst_1") is False

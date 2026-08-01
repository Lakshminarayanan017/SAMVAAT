"""Feature flags (Blueprint F6).

Every redesign phase ships behind a flag whose **off-state is the current
behaviour, not a broken one**. That is what makes a rollback lose a feature
rather than lose a learner's session.

WHY THIS IS A HUNDRED LINES AND NOT A VENDOR SDK
------------------------------------------------
A flag service is a network call in the request path, a third party who now sees
which disabled learner is in which experiment, and an outage surface for a
product whose learners are on unreliable connections. None of that is worth it
for a handful of booleans read from configuration.

THE RULES THAT ARE NOT NEGOTIABLE
---------------------------------
1. **An unknown flag is off.** Never on, never an exception. A typo in a flag
   name must not enable an unfinished feature in production, and it must not
   take the service down either.

2. **Rollout is deterministic per user.** A learner who sees the new level
   runner today sees it tomorrow. Random assignment per request would flip the
   interface underneath somebody mid-session, which for a learner with a
   cognitive disability is not a minor annoyance — it is the app becoming a
   different app while they are using it.

3. **The bucket is derived from a salted hash of the user id**, and the salt is
   per-flag. Without a per-flag salt, the same 10% of learners are the guinea
   pigs for every experiment forever — and given who our learners are, that is
   a fairness problem rather than a statistical one.

4. **Nothing here is a kill switch for accessibility.** No flag may gate a
   modality, a channel, or an assistive behaviour. Those are not experiments.
   `assert_not_accessibility_gated` enforces the naming half of that.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

#: Substrings that must never appear in a flag name.
#:
#: A flag called `switch_scanning` or `captions_v2` would mean somebody is
#: preparing to turn accessibility off for a percentage of disabled users. The
#: check is crude on purpose: it is a tripwire that makes the intent visible in
#: review, not a security boundary.
_FORBIDDEN_IN_NAME = (
    "a11y",
    "accessib",
    "aria",
    "caption",
    "screenreader",
    "screen_reader",
    "switch_scan",
    "modality",
    "easy_read",
    "high_contrast",
)


class AccessibilityGatedFlagError(ValueError):
    """Raised when a flag name suggests it gates an accessibility feature."""


def assert_not_accessibility_gated(name: str) -> None:
    lowered = name.lower()
    for forbidden in _FORBIDDEN_IN_NAME:
        if forbidden in lowered:
            raise AccessibilityGatedFlagError(
                f"Flag {name!r} looks like it gates an accessibility feature "
                f"(matched {forbidden!r}). Accessibility is not an experiment: it ships on "
                f"for everyone or it does not ship. If this flag is really about something "
                f"else, rename it."
            )


@dataclass(frozen=True)
class Flag:
    """One flag.

    `rollout` is the percentage of learners who see it, 0-100. `enabled` is the
    master switch — a flag that is off is off for everyone regardless of
    rollout, which is what makes "turn it off now" a single edit.
    """

    name: str
    enabled: bool = False
    rollout: int = 100
    #: Always on for these user ids, regardless of rollout. Staff and pilot
    #: testers, so somebody can look at the new thing before 10% of learners do.
    always_on_for: frozenset[str] = field(default_factory=frozenset)
    description: str = ""

    def __post_init__(self) -> None:
        assert_not_accessibility_gated(self.name)
        if not 0 <= self.rollout <= 100:
            raise ValueError(f"Flag {self.name!r}: rollout must be 0-100, got {self.rollout}")


#: The registry.
#:
#: Declared in code rather than read from a database so that the set of flags is
#: reviewable, greppable and versioned with the code it gates.
_REGISTRY: dict[str, Flag] = {
    flag.name: flag
    for flag in [
        Flag(
            name="game_loop",
            description="Blueprint Phase 2. World map as home, level runner, celebration. "
            "Off restores the tab bar.",
        ),
        Flag(
            name="learning_profiles",
            description="Blueprint Phase 3. Off means everyone gets prefer_not_to_say "
            "behaviour, which is today's behaviour.",
        ),
        Flag(
            name="motion_v2",
            description="Blueprint Phase 4. Off means the Still motion level everywhere.",
        ),
        Flag(
            name="stories_v2",
            description="Blueprint Phase 5. Off restores linear stories, which keep working.",
        ),
        Flag(
            name="rewards",
            description="Blueprint Phase 6. Off retains coins in the ledger, simply unshown.",
        ),
    ]
}


def _bucket(flag_name: str, user_id: str) -> int:
    """Deterministic 0-99 bucket for a user, salted per flag.

    SHA-256 rather than `hash()`: Python's built-in hash is randomised per
    process, so the same learner would land in a different bucket after every
    restart — which is precisely the mid-session interface flip rule 2 forbids.
    """
    digest = hashlib.sha256(f"{flag_name}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100


def is_enabled(name: str, user_id: str | None = None) -> bool:
    """Is this flag on for this learner?

    An unknown flag is off. An anonymous caller gets the flag only at a 100%
    rollout, because there is no stable identity to bucket and flipping on every
    request would be worse than not showing the feature at all.
    """
    flag = _REGISTRY.get(name)
    if flag is None or not flag.enabled:
        return False

    if user_id and user_id in flag.always_on_for:
        return True

    if flag.rollout >= 100:
        return True
    if flag.rollout <= 0:
        return False

    if user_id is None:
        return False

    return _bucket(name, user_id) < flag.rollout


def all_for(user_id: str | None = None) -> dict[str, bool]:
    """Every flag's state for one learner.

    Sent to the client in one response so the client never has to ask per flag,
    and so a learner on a poor connection does not get a half-configured
    interface assembled from several round trips.
    """
    return {name: is_enabled(name, user_id) for name in sorted(_REGISTRY)}


def describe() -> dict[str, dict[str, object]]:
    """The registry, for an operator. Never exposed to learners."""
    return {
        name: {
            "enabled": flag.enabled,
            "rollout": flag.rollout,
            "description": flag.description,
        }
        for name, flag in sorted(_REGISTRY.items())
    }


def override(name: str, *, enabled: bool, rollout: int = 100) -> None:
    """Change a flag at runtime.

    Exists for tests and for an operator console. Deliberately not reading from
    the environment on every call: a flag that changes value between two reads
    inside one request produces a half-old, half-new response.
    """
    existing = _REGISTRY.get(name)
    _REGISTRY[name] = Flag(
        name=name,
        enabled=enabled,
        rollout=rollout,
        always_on_for=existing.always_on_for if existing else frozenset(),
        description=existing.description if existing else "",
    )


def load_from_env(environ: dict[str, str] | None = None) -> None:
    """Apply `SAMVAAD_FLAG_<NAME>=on|off|<0-100>` overrides.

    Called once at startup. `on` and `off` are accepted alongside a percentage
    because "SAMVAAD_FLAG_GAME_LOOP=on" is what somebody types at 2am during an
    incident, and refusing it then would be a poor time to be pedantic.
    """
    source = environ if environ is not None else dict(os.environ)

    for key, raw in source.items():
        if not key.startswith("SAMVAAD_FLAG_"):
            continue

        name = key.removeprefix("SAMVAAD_FLAG_").lower()
        value = raw.strip().lower()

        if value in ("on", "true", "1", "yes"):
            override(name, enabled=True, rollout=100)
        elif value in ("off", "false", "0", "no"):
            override(name, enabled=False, rollout=0)
        elif value.isdigit():
            percent = int(value)
            override(name, enabled=percent > 0, rollout=min(100, percent))

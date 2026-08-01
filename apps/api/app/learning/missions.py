"""Mission generation and selection (Blueprint Phase 2, G2/G3).

A level names which mission *types* it contains. This module turns that into
actual missions over actual phrases, weighted by the learner's profile.

WHY SELECTION IS SERVER-SIDE
----------------------------
It could all happen in the client — the curriculum and the phrase bank are both
there. It does not, for one reason: the mission mix is where a learning profile
becomes real (Blueprint §12.4), and profile weights are the kind of thing that
must be identical for a learner across their phone, their tablet and the centre's
shared laptop. A client-side mix drifts between devices and nobody can explain
why the same learner got different practice.

THE FIVE PROPERTIES EVERY MISSION MUST HAVE (Blueprint §7.4)
------------------------------------------------------------
1. Answerable in every input channel the learner's profile offers.
2. No time limit anywhere — not a countdown, not a bonus, not a "you took a
   while" prompt.
3. Unlimited retries at no cost. No hearts, no lives, no progress lost.
4. A scaffold always available. Requesting one lowers the FSRS grade, because
   that is genuine partial recall — and never lowers XP, because XP is for
   effort.
5. A wrong answer produces coaching, never a verdict.

`tests/test_missions.py` asserts all five against every generated mission, for
every mission type. A sixth type added without those properties fails there.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

MissionType = Literal[
    "recognise",
    "choose_in_context",
    "produce",
    "order_the_steps",
    "scenario",
    "roleplay",
    "interview",
    "boss",
]

#: Mission types this module can currently generate.
#:
#: Deliberately smaller than the eight the curriculum names. The blueprint
#: sequences three first (§17 Phase 2) and the rest after, and a level whose
#: declared type is not yet buildable falls back rather than failing — a learner
#: must never meet an empty level because a mission type is unfinished.
IMPLEMENTED: frozenset[str] = frozenset({"recognise", "choose_in_context", "produce"})

#: What a level gets when none of its declared types is implemented yet.
FALLBACK_TYPE: MissionType = "recognise"

#: How many wrong options a choice mission offers alongside the right one.
DISTRACTOR_COUNT = 2

#: Missions per level. Short by design — the blueprint targets a 3-7 minute
#: session with a visible end, and the end stops being visible past about six.
MIN_MISSIONS = 3
MAX_MISSIONS = 6


@dataclass(frozen=True)
class Mission:
    """One mission, ready to render.

    `scaffold` is populated for every mission without exception. A mission with
    no way to ask for help is a mission a learner can get stuck in, and getting
    stuck with no exit is how somebody decides the app is not for them.
    """

    id: str
    type: MissionType
    block_id: str
    #: The situation. What makes this a puzzle rather than a quiz question.
    prompt: str
    #: The answer, in plain standard English. Never rendered verbatim to every
    #: learner — the modality router decides presentation.
    answer_text: str
    #: For choice missions: every option, already shuffled. Empty otherwise.
    options: tuple[str, ...] = ()
    #: Always present. See the class docstring.
    scaffold: str = ""
    #: Shown after a wrong answer. Coaching, never a verdict.
    coaching: str = ""


@dataclass
class MissionPlan:
    level_id: str
    missions: list[Mission] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.missions)


# ── prompts ──────────────────────────────────────────────────────────────────
#
# Written as situations with constraints, which is the whole difference between
# a quiz and a puzzle (Blueprint §7.1):
#
#   "Which of these means 'please repeat'?"                   -> a quiz question
#   "The machine was loud and you caught the first thing."    -> a puzzle
#
# Same phrase, same recall, entirely different experience.

_PROMPTS: dict[str, str] = {
    "recognise": "Which one means the same thing?",
    "choose_in_context": "Which one fits here?",
    "produce": "What would you say?",
}

_SCAFFOLDS: dict[str, str] = {
    "recognise": "The right one says the same thing in different words.",
    "choose_in_context": "Think about who you are talking to, and how well you know them.",
    "produce": "You can look at the words first, then say or type them.",
}


def _coaching_for(answer: str) -> str:
    """What a learner sees after a wrong answer.

    Never a verdict, and never the word "wrong". "Not quite yet" carries the
    same information and leaves the door open, which matters more than it
    sounds: this is the sentence a learner reads on the day they are already
    having a bad time.
    """
    return f"Not quite yet. The one that fits is: {answer}"


def _pick_distractors(
    correct: str, pool: list[str], rng: random.Random, count: int = DISTRACTOR_COUNT
) -> list[str]:
    """Plausible wrong options, drawn from the same level.

    Drawn from the level rather than the whole corpus on purpose. A distractor
    from a different world is obviously wrong and teaches nothing; a distractor
    from the same chapter is a phrase the learner is also learning, so choosing
    between them is the actual skill.
    """
    candidates = [text for text in pool if text != correct]
    rng.shuffle(candidates)
    return candidates[:count]


def build_missions(
    level_id: str,
    declared_types: list[str],
    phrases: list[dict],
    *,
    weights: dict[str, float] | None = None,
    seed: str | None = None,
) -> MissionPlan:
    """Turn a level into missions.

    `phrases` is a list of `{block_id, canonical_text}`. `weights` biases the mix
    toward types that suit the learner's profile — it never eliminates a type,
    because deciding somebody cannot do a kind of practice because of their
    disability is the exact harm this product exists to refuse (§12.3).

    `seed` makes the plan stable for a learner: reopening a level mid-session
    must not reshuffle it into different missions. Derived from the level and
    the learner, so two learners get different orders and one learner gets the
    same one twice.
    """
    rng = random.Random(seed or level_id)

    usable = [t for t in declared_types if t in IMPLEMENTED] or [FALLBACK_TYPE]
    texts = [p["canonical_text"] for p in phrases]

    # A level with fewer phrases than the minimum still runs. Padding it by
    # repeating a phrase would be worse than a shorter level.
    count = max(MIN_MISSIONS, min(MAX_MISSIONS, len(phrases)))
    chosen_phrases = phrases[:count]

    missions: list[Mission] = []
    for index, phrase in enumerate(chosen_phrases):
        mission_type = _weighted_choice(usable, weights, rng)
        missions.append(
            _build_one(
                level_id=level_id,
                index=index,
                mission_type=mission_type,
                phrase=phrase,
                pool=texts,
                rng=rng,
            )
        )

    return MissionPlan(level_id=level_id, missions=missions)


def _weighted_choice(
    types: list[str], weights: dict[str, float] | None, rng: random.Random
) -> MissionType:
    """Bias, never eliminate.

    A weight of zero would remove a mission type from a learner's experience
    entirely. The floor keeps every implemented type reachable, so a profile
    tilts the mix rather than deciding what somebody is capable of.
    """
    if not weights:
        return rng.choice(types)  # type: ignore[return-value]

    FLOOR = 0.05
    scored = [(t, max(FLOOR, weights.get(t, 1.0))) for t in types]
    total = sum(weight for _, weight in scored)
    target = rng.uniform(0, total)

    running = 0.0
    for mission_type, weight in scored:
        running += weight
        if running >= target:
            return mission_type  # type: ignore[return-value]
    return scored[-1][0]  # type: ignore[return-value]


def _build_one(
    *,
    level_id: str,
    index: int,
    mission_type: str,
    phrase: dict,
    pool: list[str],
    rng: random.Random,
) -> Mission:
    answer = phrase["canonical_text"]
    mission_id = f"{level_id}.m{index + 1:02d}"

    options: tuple[str, ...] = ()
    if mission_type in ("recognise", "choose_in_context"):
        candidates = [answer, *_pick_distractors(answer, pool, rng)]
        rng.shuffle(candidates)
        options = tuple(candidates)

        # A choice mission with only one option is not a choice. Falling back to
        # `produce` is better than showing a single button and calling it a
        # question.
        if len(options) < 2:
            mission_type = "produce"
            options = ()

    return Mission(
        id=mission_id,
        type=mission_type,  # type: ignore[arg-type]
        block_id=phrase["block_id"],
        prompt=_PROMPTS.get(mission_type, _PROMPTS["recognise"]),
        answer_text=answer,
        options=options,
        scaffold=_SCAFFOLDS.get(mission_type, _SCAFFOLDS["recognise"]),
        coaching=_coaching_for(answer),
    )

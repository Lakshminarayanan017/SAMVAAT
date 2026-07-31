"""The rubric's scored and excluded dimensions.

This module is the canonical machine-readable form of the list in
`docs/ETHICS_CHARTER.md` §E2. The charter is the human-readable original; a test
asserts the two agree, so editing one without the other fails the build.

WHY THE EXCLUSION LIST IS CODE AND NOT A PROMPT
------------------------------------------------
AI hiring tools have a documented record of filtering out disabled candidates by
scoring exactly these traits. We are building an interview scorer for disabled
people. If we reproduce that behaviour we have built the harm we set out to
prevent — and "we told the model not to" is not a defence anyone should accept,
least of all from us.

So the list exists in four places that enforce rather than request:

  1. `scrubber.py`      — the scorer never receives the excluded traits
  2. `SCORED_DIMENSIONS` — the response schema has no field for them
  3. the invariance test — injecting disfluency must not move a score
  4. the audit record   — every score persists what was and was not graded
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScoredDimension(str, Enum):
    """The six things the rubric may grade. There is no seventh."""

    CONTENT_RELEVANCE = "content_relevance"
    STRUCTURE_STAR = "structure_star"
    SPECIFICITY = "specificity"
    CLARITY_OF_INTENT = "clarity_of_intent"
    SELF_ADVOCACY = "self_advocacy"
    ROLE_ALIGNMENT = "role_alignment"


#: Persisted with every score, so an audit can prove what the rubric refused to
#: grade rather than relying on the absence of evidence.
EXCLUDED_DIMENSIONS: tuple[str, ...] = (
    "speech_rate",
    "articulation_quality",
    "fluency",
    "disfluency",
    "accent",
    "voice_quality",
    "gaze",
    "eye_contact",
    "facial_affect",
    "body_posture",
    "motor_stillness",
    "response_latency",
    "grammatical_perfection",
    "vocabulary_sophistication",
)


@dataclass(frozen=True)
class DimensionSpec:
    """What a dimension means, and — where it matters — what it explicitly is not."""

    dimension: ScoredDimension
    question: str
    #: Shown to the learner beside their score.
    learner_label: str
    #: The distinction that keeps this dimension off the exclusion list. Written
    #: into the scoring prompt verbatim.
    not_this: str = ""


SPECS: dict[ScoredDimension, DimensionSpec] = {
    ScoredDimension.CONTENT_RELEVANCE: DimensionSpec(
        dimension=ScoredDimension.CONTENT_RELEVANCE,
        question="Did the answer address the question that was asked?",
        learner_label="Answering the question",
    ),
    ScoredDimension.STRUCTURE_STAR: DimensionSpec(
        dimension=ScoredDimension.STRUCTURE_STAR,
        question="Are situation, task, action and result present?",
        learner_label="Telling the whole story",
        not_this="Not whether they were in order, and not whether the answer was long.",
    ),
    ScoredDimension.SPECIFICITY: DimensionSpec(
        dimension=ScoredDimension.SPECIFICITY,
        question="Are there concrete examples rather than general claims?",
        learner_label="Giving real examples",
    ),
    ScoredDimension.CLARITY_OF_INTENT: DimensionSpec(
        dimension=ScoredDimension.CLARITY_OF_INTENT,
        question="Is the point recoverable — can a listener tell what they meant?",
        learner_label="Getting the point across",
        not_this=(
            "NOT whether it was well articulated, fluent, grammatical, or "
            "expressed in sophisticated language. A point made in four plain "
            "words is perfectly clear. Score whether the meaning arrives, and "
            "nothing about how it travelled."
        ),
    ),
    ScoredDimension.SELF_ADVOCACY: DimensionSpec(
        dimension=ScoredDimension.SELF_ADVOCACY,
        question="Did they present their strengths, and state what they need?",
        learner_label="Speaking up for yourself",
        not_this=(
            "Never penalise a learner for disclosing a disability or requesting "
            "an adjustment. Asking for what you need is the skill being scored."
        ),
    ),
    ScoredDimension.ROLE_ALIGNMENT: DimensionSpec(
        dimension=ScoredDimension.ROLE_ALIGNMENT,
        question="Does the answer fit the job being discussed?",
        learner_label="Fitting the job",
    ),
}


#: Score range per dimension. 1-5 with anchored descriptions rather than 0-100:
#: a model asked for a percentage invents precision it does not have, and the
#: median of three runs is meaningless if the scale is noise.
MIN_SCORE = 1
MAX_SCORE = 5

SCORE_ANCHORS: dict[int, str] = {
    1: "not present",
    2: "briefly touched on",
    3: "present and adequate",
    4: "clear and well supported",
    5: "strong, with specific evidence",
}


def scored_dimension_names() -> tuple[str, ...]:
    return tuple(dimension.value for dimension in ScoredDimension)


def is_excluded(name: str) -> bool:
    return name.lower().strip() in EXCLUDED_DIMENSIONS


def validate_response_shape(payload: dict) -> list[str]:
    """Layer 2, at runtime.

    The schema has no field for an excluded trait, but a model can still invent
    one. Any key outside the six is rejected rather than ignored — an ignored
    extra field is an extra field that a future refactor helpfully starts
    persisting.
    """
    problems: list[str] = []

    scores = payload.get("scores")
    if not isinstance(scores, dict):
        return ["`scores` is missing or not an object"]

    allowed = set(scored_dimension_names())
    extra = set(scores) - allowed

    for name in sorted(extra):
        if is_excluded(name):
            problems.append(
                f"the rubric returned an excluded dimension '{name}' — "
                "this is an Ethics E2 breach, not a schema nit"
            )
        else:
            problems.append(f"unknown scored dimension '{name}'")

    for name in sorted(allowed - set(scores)):
        problems.append(f"missing dimension '{name}'")

    for name, value in scores.items():
        if name in allowed and not (
            isinstance(value, int) and MIN_SCORE <= value <= MAX_SCORE
        ):
            problems.append(f"'{name}' must be an integer {MIN_SCORE}-{MAX_SCORE}, got {value!r}")

    return problems

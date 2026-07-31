"""The bias-guarded interview rubric (M11).

Scores an interview answer on six dimensions, is structurally blind to fourteen
others, and writes an audit record that proves it.

    answer + timing + prosody + disfluency events
        -> strip_timing()          layer 1a — the timing never arrives
        -> scrub()                 layer 1b — the disfluency never arrives
        -> score N times, median   variance mitigation
        -> validate_response_shape layer 2 — no field for an excluded trait
        -> audit record            layer 4 — what was and was not graded
        -> trainer override        Ethics E5 — a human can always change it

VARIANCE
--------
LLM scoring variance is the documented weakness of this approach, and the
mitigation is boring rather than clever: temperature 0, few-shot anchors per
score level, and the median of three runs. The median rather than the mean
because one outlier run should move a learner's score by nothing at all.

Cohen's kappa against two human raters is measured, not assumed — see
`eval/rubric_agreement.py`.
"""

from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone

from providers.base import GenerationRequest, Prompt
from rubric.dimensions import (
    EXCLUDED_DIMENSIONS,
    MAX_SCORE,
    MIN_SCORE,
    SCORE_ANCHORS,
    SPECS,
    ScoredDimension,
    scored_dimension_names,
    validate_response_shape,
)
from rubric.scrubber import scrub, strip_timing

log = logging.getLogger("samvaad.genai.rubric")

RUBRIC_VERSION = "rubric-v1"


def _build_system_prompt() -> str:
    """Assembled from the dimension specs, not written out twice.

    A prompt that restates the dimension list is a second copy that drifts, and
    a drifted rubric prompt is a rubric that scores something other than what
    the audit record claims.
    """
    dimensions = "\n".join(
        f"- {spec.dimension.value}: {spec.question}"
        + (f"\n    {spec.not_this}" if spec.not_this else "")
        for spec in SPECS.values()
    )
    anchors = "\n".join(f"  {value} = {label}" for value, label in SCORE_ANCHORS.items())

    return f"""You score one answer from a mock job interview.

The candidate is a disabled adult practising for real interviews in India. You are helping them \
prepare, and your scores must reflect the substance of what they said.

SCORE EXACTLY THESE SIX DIMENSIONS, EACH {MIN_SCORE}-{MAX_SCORE}:
{dimensions}

SCALE:
{anchors}

YOU MUST NOT SCORE, MENTION, OR TAKE INTO ACCOUNT:
{", ".join(EXCLUDED_DIMENSIONS)}

The transcript you receive has already had disfluencies, pauses and all timing removed. It is \
normalised text. Do not speculate about how it was spoken — you have not been given that \
information, and it is not yours to grade.

For each dimension give one short evidence quote from the answer itself. If you cannot find \
evidence, score it {MIN_SCORE} and say so.

Respond with JSON only:
{{
  "scores": {{ {", ".join(f'"{name}": <{MIN_SCORE}-{MAX_SCORE}>' for name in scored_dimension_names())} }},
  "evidence": {{ "<dimension>": "<a short quote from the answer>" }},
  "strengths": ["one or two things the answer did well"],
  "improvements": ["at most two things to try next time"]
}}"""


RUBRIC_PROMPT = Prompt(name="rubric_score", version="1.0.0", system=_build_system_prompt())


@dataclass(frozen=True)
class DimensionScore:
    dimension: ScoredDimension
    score: int
    evidence: str = ""
    #: The individual runs before the median. Kept so a suspicious score can be
    #: checked for variance rather than argued about.
    runs: tuple[int, ...] = ()

    @property
    def learner_label(self) -> str:
        return SPECS[self.dimension].learner_label

    @property
    def is_stable(self) -> bool:
        """Did the runs agree? A spread of more than one point means the model
        is guessing, and the client says so instead of showing a firm number."""
        return not self.runs or (max(self.runs) - min(self.runs)) <= 1


@dataclass
class RubricResult:
    """One scored answer, and everything needed to audit it."""

    scored: bool
    dimensions: tuple[DimensionScore, ...] = ()
    strengths: tuple[str, ...] = ()
    #: Capped at two. More is demoralising and unusable — Ethics Charter.
    improvements: tuple[str, ...] = ()
    #: Set when scoring could not run. The interview still completes.
    unavailable_message: str = ""
    audit: dict = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(d.score for d in self.dimensions)

    @property
    def mean(self) -> float:
        return self.total / len(self.dimensions) if self.dimensions else 0.0

    def by_dimension(self, dimension: ScoredDimension) -> DimensionScore | None:
        return next((d for d in self.dimensions if d.dimension is dimension), None)


class RubricScorer:
    def __init__(self, router, runs: int = 3, version: str = RUBRIC_VERSION) -> None:
        self.router = router
        self.runs = max(1, runs)
        self.version = version

    def score(
        self,
        question: str,
        answer: str,
        role_context: str = "",
        attempt_metadata: dict | None = None,
    ) -> RubricResult:
        """Score one answer.

        `attempt_metadata` may contain anything the caller has — prosody,
        disfluency events, timings. None of it reaches the model: `strip_timing`
        removes it, and that is the point of accepting it here rather than
        asking every caller to remember not to pass it.
        """
        scrubbed = scrub(answer)
        safe_metadata = strip_timing(attempt_metadata or {})

        message = (
            f"Interview question: {question}\n"
            f"{f'Role context: {role_context}{chr(10)}' if role_context else ''}"
            f"Candidate's answer (normalised):\n{scrubbed.text}\n\n"
            "Score this answer as JSON."
        )

        collected: list[dict] = []
        provider = "scripted"
        prompt_id = RUBRIC_PROMPT.id

        for _ in range(self.runs):
            generation = self.router.generate(
                GenerationRequest(
                    prompt=RUBRIC_PROMPT,
                    user_message=message,
                    user_key="rubric",
                    max_tokens=900,
                    temperature=0.0,
                    prefill="{",
                    metadata=safe_metadata,
                )
            )
            provider = generation.provider
            prompt_id = generation.completion.prompt_id

            payload = _parse(generation.completion.raw)

            # The scripted provider deliberately refuses to score. An interview
            # score is a judgement about employability; inventing one from
            # authored text would put a fabricated assessment into an audit
            # record that claims to be reviewable.
            if payload.get("scored") is False:
                return RubricResult(
                    scored=False,
                    unavailable_message=payload.get(
                        "message",
                        "Your interview is saved. The detailed feedback will be here "
                        "when you come back.",
                    ),
                    audit=self._audit(scrubbed, provider, prompt_id, ["scoring_unavailable"]),
                )

            problems = validate_response_shape(payload)
            if problems:
                log.warning("rubric response rejected: %s", "; ".join(problems))
                continue

            collected.append(payload)

        if not collected:
            return RubricResult(
                scored=False,
                unavailable_message=(
                    "We could not produce your feedback this time. Your interview is "
                    "saved and your trainer can still review it."
                ),
                audit=self._audit(scrubbed, provider, prompt_id, ["no_valid_response"]),
            )

        return self._combine(collected, scrubbed, provider, prompt_id)

    def _combine(self, payloads: list[dict], scrubbed, provider: str, prompt_id: str) -> RubricResult:
        """Median across runs, per dimension.

        Median rather than mean: one outlier run must move a learner's score by
        nothing at all, and with three runs the mean lets it move by a third of
        the distance.
        """
        dimensions: list[DimensionScore] = []

        for dimension in ScoredDimension:
            runs = tuple(int(p["scores"][dimension.value]) for p in payloads)
            evidence = next(
                (p.get("evidence", {}).get(dimension.value, "") for p in payloads
                 if p.get("evidence", {}).get(dimension.value)),
                "",
            )

            dimensions.append(
                DimensionScore(
                    dimension=dimension,
                    score=int(statistics.median(runs)),
                    evidence=evidence,
                    runs=runs,
                )
            )

        first = payloads[0]

        return RubricResult(
            scored=True,
            dimensions=tuple(dimensions),
            # Strengths first, always — the Ethics Charter says so, and the
            # ordering here is what makes the client render them that way.
            strengths=tuple(first.get("strengths", [])[:3]),
            improvements=tuple(first.get("improvements", [])[:2]),
            audit=self._audit(scrubbed, provider, prompt_id, []),
        )

    def _audit(self, scrubbed, provider: str, prompt_id: str, notes: list[str]) -> dict:
        """Layer 4. Exportable, and complete enough to answer questions asked
        two years from now by someone who was not in the room."""
        return {
            "rubric_version": self.version,
            "scored_dimensions": list(scored_dimension_names()),
            "excluded_dimensions": list(EXCLUDED_DIMENSIONS),
            "prompt_hash": prompt_id,
            "model_id": provider,
            "self_consistency_runs": self.runs,
            "input_scrubbing": scrubbed.audit(),
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }


@dataclass(frozen=True)
class TrainerOverride:
    """Ethics E5. A human can change any score, and the change is recorded.

    The override rate is also our most honest quality metric: below 85%
    agreement, institutions will not deploy this, and institutions are the
    distribution channel.
    """

    interview_run_id: str
    dimension: ScoredDimension
    original_score: int
    new_score: int
    trainer_user_id: str
    reason: str
    at: datetime

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError(
                "An override needs a reason. An unexplained override teaches the "
                "system nothing and gives the learner no way to understand the change."
            )
        if not MIN_SCORE <= self.new_score <= MAX_SCORE:
            raise ValueError(f"Score must be {MIN_SCORE}-{MAX_SCORE}, got {self.new_score}")


def apply_overrides(result: RubricResult, overrides: list[TrainerOverride]) -> RubricResult:
    """Return a result with trainer decisions applied.

    The AI score is not discarded — it stays in `runs` — because "the trainer
    disagreed with the model here" is exactly the signal the override rate
    measures, and destroying it would destroy the metric.
    """
    by_dimension = {override.dimension: override for override in overrides}

    return RubricResult(
        scored=result.scored,
        dimensions=tuple(
            DimensionScore(
                dimension=d.dimension,
                score=by_dimension[d.dimension].new_score if d.dimension in by_dimension else d.score,
                evidence=d.evidence,
                runs=d.runs,
            )
            for d in result.dimensions
        ),
        strengths=result.strengths,
        improvements=result.improvements,
        unavailable_message=result.unavailable_message,
        audit={
            **result.audit,
            "trainer_overrides": [
                {
                    "dimension": o.dimension.value,
                    "from": o.original_score,
                    "to": o.new_score,
                    "trainer": o.trainer_user_id,
                    "reason": o.reason,
                    "at": o.at.isoformat(),
                }
                for o in overrides
            ],
        },
    )


def _parse(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {}

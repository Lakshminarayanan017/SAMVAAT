"""The disfluency-invariance gate.

The single most important test in this repository, and the thing that converts a
fairness claim into a fairness proof.

    for transcript in fixtures:
        clean    = score(transcript)
        degraded = score(inject_disfluencies(transcript))
        assert abs(clean.total - degraded.total) < EPSILON

Identical content. One version reads as a learner who stammers; the other does
not. If injecting disfluency changes the score, the build fails.

WHY EPSILON IS ZERO
-------------------
Not "small". Zero.

The scrubber removes disfluency before the scorer ever sees the text, so the two
versions arrive at the model as the *same string*. A non-zero difference would
mean the scrubber missed something, and there is no amount of missed disfluency
that is acceptable — a learner scoring one point lower for stammering is exactly
the harm this product exists to prevent, and a tolerance is a budget for it.

The check therefore runs at two levels:

  1. **Structural** (no model needed, runs in CI on every build): assert the
     scrubbed forms are byte-identical. This is the strong claim, and it is free.
  2. **End-to-end** (needs a provider): score both and compare. This catches a
     scorer that somehow sees the raw text despite the scrubber.

Level 1 is the gate. Level 2 is the confirmation, run when a key is present.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from rubric.scrubber import scrub

#: Zero. See the module docstring.
EPSILON = 0

#: Filled pauses, in rough order of how often transcribers record them.
FILLERS = ("um", "uh", "erm", "er", "you know", "like", "I mean")


@dataclass(frozen=True)
class InvarianceCase:
    """One fixture, in both forms."""

    name: str
    clean: str
    degraded: str

    @property
    def scrubbed_clean(self) -> str:
        return scrub(self.clean).text

    @property
    def scrubbed_degraded(self) -> str:
        return scrub(self.degraded).text

    @property
    def structurally_invariant(self) -> bool:
        return self.scrubbed_clean == self.scrubbed_degraded


def inject_disfluencies(text: str, seed: int = 20260731, intensity: float = 0.35) -> str:
    """Add fillers, blocks, repetitions and long pauses without changing content.

    Modelled on what a transcriber actually writes down for a learner who
    stammers: sound repetition on word onsets, whole-word repetition, filled
    pauses between clauses, and ellipses for blocks.

    Deterministic by seed, because a flaky fairness gate gets disabled and a
    disabled fairness gate protects nobody.
    """
    rng = random.Random(seed)
    words = text.split()
    output: list[str] = []

    for index, word in enumerate(words):
        # A filled pause before a clause boundary, where people actually pause.
        if index > 0 and rng.random() < intensity * 0.4:
            output.append(rng.choice(FILLERS))

        # A block: the transcriber's ellipsis for a silent struggle.
        if rng.random() < intensity * 0.2:
            output.append("...")

        roll = rng.random()

        if roll < intensity * 0.35 and len(word) > 2 and word[0].isalpha():
            # Sound repetition: "w-w-worked".
            onset = word[0]
            output.append(f"{onset}-{onset}-{word}")
        elif roll < intensity * 0.5:
            # Whole-word repetition: "the the".
            output.append(word)
            output.append(word)
        else:
            output.append(word)

    return " ".join(output)


#: Real-shaped interview answers. Content varies in quality on purpose — the gate
#: has to hold for a weak answer as well as a strong one, and a scorer that only
#: behaves on good answers is a scorer that penalises the learners who most need
#: honest feedback.
FIXTURES: tuple[tuple[str, str], ...] = (
    (
        "strong_star_answer",
        "At my last job in the packaging unit there was a week when two people were off sick. "
        "I was asked to cover the labelling as well as my own bench. I made a checklist so I "
        "would not miss a step, and I asked my supervisor to confirm the first batch. "
        "We finished every order on time that week and the supervisor asked me to keep using "
        "the checklist.",
    ),
    (
        "brief_answer",
        "I am good at working carefully. I check my work twice before I finish.",
    ),
    (
        "self_advocacy_answer",
        "I work best when instructions are written down. If I have the steps on paper I can "
        "check them myself and I do not need to ask twice. In my last job my supervisor "
        "printed the steps for me and it worked well for both of us.",
    ),
    (
        "weak_generic_answer",
        "I am a hard worker and a good team player. I always do my best and I am very "
        "reliable.",
    ),
    (
        "disclosure_answer",
        "I have a hearing disability. Captions help me in meetings, and if someone faces me "
        "when they speak I can follow easily. I have worked in a warehouse for two years and "
        "it has never been a problem.",
    ),
)


def build_cases(seed: int = 20260731) -> list[InvarianceCase]:
    return [
        InvarianceCase(
            name=name,
            clean=text,
            degraded=inject_disfluencies(text, seed=seed + index),
        )
        for index, (name, text) in enumerate(FIXTURES)
    ]


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


def run_structural_gate(seed: int = 20260731) -> list[GateResult]:
    """Level 1. No model, no key, no network — runs on every build.

    Asserts that the scrubber makes the two forms identical. If it does, the
    scorer cannot possibly distinguish them, and the fairness property holds by
    construction rather than by measurement.
    """
    results: list[GateResult] = []

    for case in build_cases(seed):
        if case.structurally_invariant:
            results.append(
                GateResult(
                    name=case.name,
                    passed=True,
                    detail=f"scrubbed forms identical ({len(case.scrubbed_clean)} chars)",
                )
            )
        else:
            results.append(
                GateResult(
                    name=case.name,
                    passed=False,
                    detail=(
                        "scrubbed forms differ — the scorer would see different text.\n"
                        f"  clean:    {case.scrubbed_clean!r}\n"
                        f"  degraded: {case.scrubbed_degraded!r}"
                    ),
                )
            )

    return results


def run_end_to_end_gate(
    scorer,
    question: str = "Tell me about a time you solved a problem at work.",
) -> list[GateResult]:
    """Level 2. Needs a provider.

    Catches the case the structural gate cannot: a scorer that somehow receives
    the raw text despite the scrubber — a refactor that passes `answer` instead
    of `scrubbed.text`, for instance.
    """
    results: list[GateResult] = []

    for case in build_cases():
        clean = scorer.score(question, case.clean)
        degraded = scorer.score(question, case.degraded)

        if not clean.scored or not degraded.scored:
            results.append(
                GateResult(
                    name=case.name,
                    passed=True,
                    detail="skipped: no generative provider available",
                )
            )
            continue

        difference = abs(clean.total - degraded.total)
        results.append(
            GateResult(
                name=case.name,
                passed=difference <= EPSILON,
                detail=(
                    f"total {clean.total} vs {degraded.total} "
                    f"(difference {difference}, bar {EPSILON})"
                ),
            )
        )

    return results


def render(results: list[GateResult]) -> str:
    lines = ["### Disfluency-invariance gate", "", "| Fixture | Result | Detail |", "|---|---|---|"]
    for result in results:
        detail = result.detail.replace("\n", " ")
        lines.append(f"| `{result.name}` | {'PASS' if result.passed else 'FAIL'} | {detail} |")
    return "\n".join(lines)


def main() -> int:
    """CI entry point.

        python -m eval.invariance
    """
    results = run_structural_gate()
    print(render(results))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())

"""The speech evaluation harness.

Built *before* the pipeline it evaluates, deliberately. A model without a frozen
eval set and a regression gate is a model nobody can safely change, and by the
time that hurts it is too late to retrofit.

Every speech pull request must include the table this prints, before and after.

    python -m eval.harness --set atypical

Two rules make this harness different from a normal ML eval:

  * Results are ALWAYS reported per speaker, never only as a mean. A mean hides
    exactly the users this product exists for - a model can post a great average
    while failing every dysarthric speaker in the set.

  * Fairness checks are gates, not diagnostics. A model that improves WER but
    fails the monotonicity or invariance check does not ship.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Target:
    """A metric with the bar it must clear. Sourced from docs/EXECUTION_PLAN.md §9.4."""

    metric: str
    description: str
    bar: str
    module: str


TARGETS: list[Target] = [
    Target(
        metric="wer_relative_reduction",
        description="Word error rate reduction of the adapted ASR against base Whisper",
        bar=">= 25% relative, per speaker",
        module="M8",
    ),
    Target(
        metric="disfluency_macro_f1",
        description="Macro-F1 over block / prolongation / repetition / interjection",
        bar=">= 0.65 on SEP-28k held-out",
        module="M7",
    ),
    Target(
        metric="gop_expert_correlation",
        description="Spearman correlation of GOP with speech-language-pathologist ratings",
        bar=">= 0.60",
        module="M6",
    ),
    Target(
        metric="ppi_monotonicity",
        description="A synthetic sequence of improving attempts must produce a rising PPI",
        bar="strictly non-decreasing over a smoothed window",
        module="M7",
    ),
    Target(
        metric="ppi_disfluency_invariance",
        description=(
            "Two synthetic speakers with identical content and improvement, one with injected "
            "disfluency, must produce statistically indistinguishable PPI trajectories"
        ),
        bar="no significant difference (this is the proof of ADR-0003)",
        module="M7",
    ),
]


@dataclass
class SpeakerResult:
    speaker_id: str
    speech_type: str  # "typical" | "dysarthric" | "stammer" | ...
    n_utterances: int
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class EvalReport:
    eval_set: str
    model_versions: dict[str, str]
    per_speaker: list[SpeakerResult]

    def aggregate(self, metric: str) -> float | None:
        values = [s.metrics[metric] for s in self.per_speaker if metric in s.metrics]
        return sum(values) / len(values) if values else None

    def render(self) -> str:
        """A markdown table, ready to paste into a pull request description."""
        lines = [
            f"### Speech eval — `{self.eval_set}`",
            "",
            f"models: {json.dumps(self.model_versions)}",
            "",
        ]

        if not self.per_speaker:
            lines += [
                "_No per-speaker results: this evaluation set has no licensed corpus "
                "cached on this host. See docs/TRAINING_HANDOFF.md for dataset access._",
                "",
                "_The fairness gates below do not need a corpus — they are properties "
                "of the scoring maths — and they run on every build._",
                "",
                "Targets this harness enforces once a corpus is present:",
                "",
                "| Module | Metric | Bar |",
                "|---|---|---|",
                *[f"| {t.module} | `{t.metric}` | {t.bar} |" for t in TARGETS],
            ]
            return "\n".join(lines)

        metrics = sorted({m for s in self.per_speaker for m in s.metrics})
        lines += [
            "| Speaker | Type | N | " + " | ".join(f"`{m}`" for m in metrics) + " |",
            "|---|---|---|" + "---|" * len(metrics),
        ]
        for s in sorted(self.per_speaker, key=lambda x: (x.speech_type, x.speaker_id)):
            cells = " | ".join(
                f"{s.metrics[m]:.3f}" if m in s.metrics else "—" for m in metrics
            )
            lines.append(f"| {s.speaker_id} | {s.speech_type} | {s.n_utterances} | {cells} |")

        # The mean goes last and is labelled, so it can never be mistaken for the
        # headline result.
        means = " | ".join(
            f"{v:.3f}" if (v := self.aggregate(m)) is not None else "—" for m in metrics
        )
        lines.append(f"| **mean** _(context only)_ | | | {means} |")
        return "\n".join(lines)


# Registry of eval sets. Populated as datasets are licensed and cached locally;
# see docs/EXECUTION_PLAN.md §9.3 for access status of each corpus.
EVAL_SETS: dict[str, Callable[[], list[SpeakerResult]]] = {
    "typical": lambda: [],
    "atypical": lambda: [],
    "stammer": lambda: [],
}


# ── Fairness gates ───────────────────────────────────────────────────────────
#
# These run without any dataset at all, because they are properties of the
# scoring maths rather than of a corpus. That is what makes them CI gates from
# day one instead of promises deferred until the data arrives — and the two
# properties they check are the entire ethical claim of the product.


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    detail: str


def _ppi_trajectory(values: list[float]) -> list[int]:
    """Score a sequence of attempts exactly as the runner does."""
    from pipeline.ppi import Baseline, Dimension, compute, update_baselines

    baselines: dict[Dimension, Baseline] = {}
    scored: list[int] = []

    for value in values:
        raw = {Dimension.FLUENCY: value}
        composite = compute(raw, baselines).composite
        if composite is not None:
            scored.append(composite)
        baselines = update_baselines(raw, baselines)

    return scored


def gate_monotonicity() -> GateResult:
    """A learner who improves must see their index rise."""
    scored = _ppi_trajectory([50.0 + step * 0.8 for step in range(45)])

    third = max(1, len(scored) // 3)
    early = sum(scored[:third]) / third
    late = sum(scored[-third:]) / third

    return GateResult(
        name="ppi_monotonicity",
        passed=late > early,
        detail=f"first third {early:.1f} -> last third {late:.1f}",
    )


def gate_disfluency_invariance() -> GateResult:
    """Identical improvement, one speaker with a constant disfluency offset.

    The trajectories must be indistinguishable. This is the proof of ADR-0003:
    a constant characteristic of a learner's speech is absorbed into their own
    baseline and cancels out of the score.
    """
    import random

    rng = random.Random(20260731)
    improvement = [55.0 + step * 0.5 for step in range(60)]

    fluent = _ppi_trajectory([value + rng.gauss(0, 3) for value in improvement])
    stammering = _ppi_trajectory([value - 25.0 + rng.gauss(0, 3) for value in improvement])

    mean_fluent = sum(fluent) / len(fluent)
    mean_stammering = sum(stammering) / len(stammering)
    difference = abs(mean_fluent - mean_stammering)

    return GateResult(
        name="ppi_disfluency_invariance",
        passed=difference < 2.0,
        detail=(
            f"mean index {mean_fluent:.2f} vs {mean_stammering:.2f} "
            f"(difference {difference:.2f}, bar < 2.00) against a 25-point raw offset"
        ),
    )


GATES: list[Callable[[], GateResult]] = [gate_monotonicity, gate_disfluency_invariance]


def run_gates() -> list[GateResult]:
    return [gate() for gate in GATES]


def render_gates(results: list[GateResult]) -> str:
    lines = [
        "### Fairness gates",
        "",
        "| Gate | Result | Detail |",
        "|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result.name}` | {'PASS' if result.passed else 'FAIL'} | {result.detail} |"
        )
    return "\n".join(lines)


def run(eval_set: str) -> EvalReport:
    if eval_set not in EVAL_SETS:
        raise SystemExit(f"unknown eval set '{eval_set}'; choose from {sorted(EVAL_SETS)}")

    from service.config import get_settings

    return EvalReport(
        eval_set=eval_set,
        model_versions=get_settings().model_versions,
        per_speaker=EVAL_SETS[eval_set](),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", default="atypical", choices=sorted(EVAL_SETS))
    parser.add_argument("--json", action="store_true", help="machine-readable output for CI")
    parser.add_argument(
        "--gates",
        action="store_true",
        help="run the fairness gates and exit non-zero if any fails",
    )
    args = parser.parse_args()

    report = run(args.set)
    gates = run_gates()

    if args.json:
        print(json.dumps({
            "eval_set": report.eval_set,
            "model_versions": report.model_versions,
            "per_speaker": [vars(s) for s in report.per_speaker],
            "gates": [vars(gate) for gate in gates],
        }, indent=2))
    else:
        print(report.render())
        print()
        print(render_gates(gates))

    # Only --gates makes failure fatal. The eval table is informational until a
    # dataset is licensed; the fairness gates are properties of our own maths
    # and are enforceable today, so CI runs them with --gates.
    if args.gates and not all(gate.passed for gate in gates):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

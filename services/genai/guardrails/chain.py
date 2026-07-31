"""The guardrail chain.

Every generated turn passes through every check before a learner sees it. The
chain is ordered cheapest-first, and it does not stop at the first failure —
knowing that a turn broke three rules rather than one is what tells you whether
the prompt needs a tweak or a rewrite.

WHAT HAPPENS ON FAILURE
-----------------------
    fail -> repair-retry once (the model is told exactly what broke)
         -> still failing? scripted fallback
         -> the learner sees a slightly less interesting conversation

A learner never sees a guardrail failure. They are not a party to our
disagreement with a language model.

WHY THIS IS NOT "JUST PROMPT IT BETTER"
---------------------------------------
Because a prompt is a request and a check is a guarantee. The condescension
filter in particular exists because "do not be patronising" in a system prompt
is a suggestion that a model will follow most of the time — and "most of the
time" applied to a disabled learner being talked down to is not a standard
anybody should accept.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

log = logging.getLogger("samvaad.genai.guardrails")


class Severity(str, Enum):
    """How a failure is handled.

    BLOCK means the turn is discarded even if everything else passed. WARN means
    it is recorded and served — used for checks that are genuinely advisory,
    like readability slightly overshooting its target.
    """

    BLOCK = "block"
    WARN = "warn"


@dataclass(frozen=True)
class Violation:
    check: str
    severity: Severity
    reason: str
    #: Fed into the repair-retry so the model is told precisely what to fix.
    #: Vague repair instructions produce vague repairs.
    repair_hint: str = ""


@dataclass
class GuardrailReport:
    violations: list[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(v.severity is Severity.BLOCK for v in self.violations)

    @property
    def blocked_by(self) -> list[str]:
        return [v.check for v in self.violations if v.severity is Severity.BLOCK]

    def repair_instructions(self) -> str:
        """What to tell the model on the retry."""
        hints = [v.repair_hint or v.reason for v in self.violations if v.severity is Severity.BLOCK]
        if not hints:
            return ""
        return (
            "Your previous response was rejected. Fix all of the following and "
            "return the corrected JSON only:\n- " + "\n- ".join(hints)
        )

    def audit(self) -> dict:
        """Persisted with the generation. An audit two years later has to be
        able to say what was checked, not merely that checking happened."""
        return {
            "passed": self.passed,
            "violations": [
                {"check": v.check, "severity": v.severity.value, "reason": v.reason}
                for v in self.violations
            ],
        }


@dataclass(frozen=True)
class GuardrailContext:
    """Everything a check might need. Passed whole so adding a check does not
    change the signature of the chain."""

    #: The parsed generation.
    payload: dict
    #: Difficulty tier 1-5, governing the allowed vocabulary.
    difficulty: int = 3
    #: 'standard' or 'easy_read', from the learner's profile.
    text_complexity: str = "standard"
    #: Phrase ids the scenario is grounded in.
    allowed_phrase_ids: frozenset[str] = frozenset()
    #: Terms the scenario legitimately introduces beyond the tier word list.
    scenario_terms: frozenset[str] = frozenset()
    scenario_setting: str = "workplace"


class Guardrail(Protocol):
    name: str
    severity: Severity

    def check(self, context: GuardrailContext) -> Violation | None: ...


def run_chain(chain: list[Guardrail], context: GuardrailContext) -> GuardrailReport:
    """Run every check. Never short-circuits.

    A check that raises is treated as a BLOCK rather than allowed through: a
    guardrail that failed to run has not established that the content is safe,
    and defaulting to permissive on error is how a safety layer quietly stops
    being one.
    """
    report = GuardrailReport()

    for guardrail in chain:
        try:
            violation = guardrail.check(context)
        except Exception as error:  # noqa: BLE001 - a broken check must not open the gate
            log.exception("guardrail %s raised", guardrail.name)
            report.violations.append(
                Violation(
                    check=guardrail.name,
                    severity=Severity.BLOCK,
                    reason=f"check failed to run: {type(error).__name__}",
                    repair_hint="",
                )
            )
            continue

        if violation is not None:
            report.violations.append(violation)

    return report

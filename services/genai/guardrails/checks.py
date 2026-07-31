"""The individual guardrails.

Ordered in `roleplay_chain()` cheapest-first. Each one answers a single question
and explains itself well enough that the repair-retry can act on it.

The condescension check is the one that does not exist in other products, and it
is the reason this file is worth reading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from guardrails.chain import GuardrailContext, Severity, Violation

# ── 1. Schema ────────────────────────────────────────────────────────────────


@dataclass
class SchemaCheck:
    """Required fields present, of the right shape.

    First because it is nearly free and because everything downstream assumes
    it passed. A missing `npc_utterance` would otherwise surface as a blank
    speech bubble, which a learner reads as the app being broken.
    """

    required: tuple[str, ...]
    name: str = "schema"
    severity: Severity = Severity.BLOCK

    def check(self, context: GuardrailContext) -> Violation | None:
        missing = [field for field in self.required if not context.payload.get(field)]

        if missing:
            return Violation(
                check=self.name,
                severity=self.severity,
                reason=f"missing required fields: {', '.join(missing)}",
                repair_hint=f"Include every required field: {', '.join(self.required)}.",
            )
        return None


# ── 2. Vocabulary ────────────────────────────────────────────────────────────

#: Words a tier-1 or tier-2 turn may use beyond the phrase bank.
#:
#: Sized deliberately. An earlier, much shorter list blocked an authored turn
#: for using "makes", "sense", "easy" and "sort" — words no learner at any tier
#: is troubled by. A vocabulary guardrail that fires on ordinary English is not
#: protecting anyone; it is producing stilted turns and training the team to
#: ignore the check.
#:
#: This is roughly the first 500 words of general English by frequency, plus the
#: closed-class words that hold sentences together. Curated rather than
#: generated from a corpus, because a raw frequency list also contains plenty of
#: words that are common in newspapers and wrong here.
CORE_VOCABULARY = frozenset(
    """
    a able about above across after again against all almost along already also
    always am an and another any anyone anything are around as ask asked asking
    at away back bad be because been before being best better between big both
    bring but buy by call called came can cannot come coming could day days did
    different do does doing done door down during each early easy end enough
    even ever every everyone everything few find fine finish finished first fix
    follow following for found from front full get getting give given go goes
    going gone good got great had half hand happen happened happy hard has have
    having he hear heard held help here hers him his hold home hope hour hours
    how however i if in into is it its job just keep kept kind knew know known
    large last late later learn least leave left less let like little long look
    looking lot made make makes making many may maybe me mean means meet met
    might mind minute minutes more morning most move much must my near need
    needs never new next nice no not nothing now number of off often okay old
    on once one only open or order other others our out over own part people
    perhaps person place please point put quite ran reach read ready real
    really right room said same saw say saying says second see seen sense sent
    set several she short should show side simple since sit small so some
    someone something soon sort sound speak spoke start started still stop
    such sure take taken talk tell than thank thanks that the their them then
    there these they thing things think this those though thought three through
    time times to today together told too took try trying turn two under
    understand until up us use used usually very wait want wanted was way we
    week well went were what when where whether which while who whole why will
    with within without word words work working would write written wrong year
    years yes yet you your yours
    """.split()
)

#: Terms every workplace scenario may use regardless of tier — they are the
#: subject matter, and removing them would leave a role-play that cannot discuss
#: work.
WORKPLACE_TERMS = frozenset(
    """
    batch break colleague customer email form job leave machine manager
    meeting morning order report safety shift supervisor task team training
    uniform workplace
    """.split()
)


@dataclass
class VocabularyCheck:
    """Keeps a turn inside the difficulty tier's word list.

    Only applied at tiers 1-2. Above that the point of the exercise is exposure
    to real workplace language, and a vocabulary cage would defeat it.
    """

    name: str = "vocabulary"
    severity: Severity = Severity.BLOCK
    #: Proportion of out-of-list words tolerated before blocking. Not zero: one
    #: unfamiliar word in a sentence is how vocabulary is learned, and a hard
    #: zero produces stilted turns that teach nothing.
    tolerance: float = 0.12

    def check(self, context: GuardrailContext) -> Violation | None:
        if context.difficulty > 2:
            return None

        utterance = str(context.payload.get("npc_utterance", ""))
        words = _words(utterance)
        if not words:
            return None

        allowed = CORE_VOCABULARY | WORKPLACE_TERMS | {
            word for term in context.scenario_terms for word in _words(term)
        }

        unknown = [word for word in words if word not in allowed]

        if len(unknown) / len(words) > self.tolerance:
            return Violation(
                check=self.name,
                severity=self.severity,
                reason=f"tier {context.difficulty} turn uses {', '.join(sorted(set(unknown))[:6])}",
                repair_hint=(
                    "Use simpler, more common words. Avoid: "
                    f"{', '.join(sorted(set(unknown))[:6])}."
                ),
            )
        return None


# ── 3. Scope ─────────────────────────────────────────────────────────────────

#: Subjects a workplace role-play has no business raising. Not a general safety
#: filter — that is the next check — but a scope boundary: a learner practising
#: how to ask for leave should not find themselves in a conversation about
#: politics, religion, or their medical history.
OUT_OF_SCOPE = (
    r"\b(politic|election|religio|caste|astrolog|horoscope)\w*",
    r"\b(diagnos|prescrib|medication|therapy session|symptom)\w*",
    r"\b(invest|stock market|cryptocurrenc|loan|gambl)\w*",
    r"\b(dating|romantic|flirt)\w*",
)


@dataclass
class ScopeCheck:
    name: str = "scope"
    severity: Severity = Severity.BLOCK

    def check(self, context: GuardrailContext) -> Violation | None:
        utterance = str(context.payload.get("npc_utterance", "")).lower()

        for pattern in OUT_OF_SCOPE:
            match = re.search(pattern, utterance)
            if match:
                return Violation(
                    check=self.name,
                    severity=self.severity,
                    reason=f"left the workplace scenario: {match.group(0)!r}",
                    repair_hint=(
                        "Stay inside the workplace scenario. Do not raise medical, "
                        "financial, political, religious or personal-life topics."
                    ),
                )
        return None


# ── 4. Safety ────────────────────────────────────────────────────────────────

UNSAFE = (
    r"\b(stupid|idiot|useless|worthless|pathetic)\b",
    r"\b(shut up|get out|go away)\b",
    r"\b(kill|suicide|self.harm|hurt yourself)\w*",
    r"\b(fired|sacked) (on the spot|right now|immediately)\b",
)


@dataclass
class SafetyCheck:
    """Harassment, abuse and cruelty.

    An interviewer persona may be brisk. It may not be abusive. The learner
    chose to practise a difficult conversation, not to be insulted, and a
    "realistic bad employer" scenario that crosses into abuse teaches nothing
    except that the app is unsafe.
    """

    name: str = "safety"
    severity: Severity = Severity.BLOCK

    def check(self, context: GuardrailContext) -> Violation | None:
        utterance = str(context.payload.get("npc_utterance", "")).lower()

        for pattern in UNSAFE:
            match = re.search(pattern, utterance)
            if match:
                return Violation(
                    check=self.name,
                    severity=self.severity,
                    reason=f"unsafe content: {match.group(0)!r}",
                    repair_hint=(
                        "Be professional. The character may be direct or "
                        "impatient, never insulting or cruel."
                    ),
                )
        return None


# ── 5. Condescension ─────────────────────────────────────────────────────────
#
# The check no other product has, and the one this file exists for.
#
# A language model asked to talk to a disabled learner will, unprompted and with
# every good intention, produce the register people use with children. "Well
# done for trying!" "That's very brave of you!" "Don't worry, we'll go nice and
# slow." Each is kind. Together they are the thing every disabled adult has
# spent their life being subjected to, and they will drive a learner away faster
# than any amount of difficulty.
#
# Three signals, because no single one is reliable:
#   * infantilising praise      — praise for existing rather than for doing
#   * pity framing              — sympathy nobody asked for
#   * diminishing constructions — "just", "simply", "even you"

INFANTILISING = (
    r"\b(good boy|good girl|clever (boy|girl)|there there)\b",
    r"\b(well done|good job|great job) for (trying|attempting|coming|being)\b",
    r"\byou('re| are) (so|very) (brave|inspiring|special|amazing)\b",
    r"\bwhat a (star|champion|trooper)\b",
    r"\b(bless you|poor (thing|you))\b",
    r"\bdon'?t worry your\b",
)

PITY = (
    r"\b(despite|even with|in spite of) your (disability|condition|difficulties|problems)\b",
    r"\b(suffer|suffering|afflicted|victim) (from|of|with)\b",
    r"\bit must be (so|very) (hard|difficult) (for you|being)\b",
    r"\byou poor\b",
    r"\bspecial needs\b",
    r"\bwheelchair.bound\b",
    r"\bconfined to\b",
)

DIMINISHING = (
    r"\beven (you|someone like you) can\b",
    r"\bjust try your (little )?best\b",
    r"\bthat'?s (okay|fine|alright) for (someone|people) like you\b",
    r"\bwe'?ll go (nice and |really )?slow(ly)? for you\b",
    r"\bi'?ll speak (nice and )?slowly (for you|so you can)\b",
    r"\bdo you understand\?.*\?",  # repeated comprehension checking
)

CONDESCENSION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("infantilising", INFANTILISING),
    ("pity", PITY),
    ("diminishing", DIMINISHING),
)


@dataclass
class CondescensionCheck:
    name: str = "condescension"
    severity: Severity = Severity.BLOCK

    def check(self, context: GuardrailContext) -> Violation | None:
        # Checked across every learner-facing string in the payload, not only
        # the utterance. A patronising hint is exactly as damaging as a
        # patronising line of dialogue, and it is easier to overlook.
        text = " ".join(
            str(value)
            for key, value in _flatten(context.payload)
            if key in _LEARNER_FACING and isinstance(value, str)
        ).lower()

        for kind, patterns in CONDESCENSION_PATTERNS:
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return Violation(
                        check=self.name,
                        severity=self.severity,
                        reason=f"{kind}: {match.group(0)!r}",
                        repair_hint=(
                            "Speak to the learner as a competent adult colleague. "
                            "No praise for effort alone, no sympathy for their "
                            "disability, no offers to slow down for them. Be warm "
                            "and ordinary, the way you would with any colleague."
                        ),
                    )
        return None


#: Payload keys a learner actually reads.
_LEARNER_FACING = frozenset(
    {
        "npc_utterance",
        "easy_read_version",
        "hint",
        "sentence_starter",
        "message",
        "text",
        "question",
        "title",
    }
)


# ── 6. Readability ───────────────────────────────────────────────────────────


@dataclass
class ReadabilityCheck:
    """Matches sentence length to the learner's text complexity.

    A WARN rather than a BLOCK, deliberately. A turn one word over the limit is
    worse than the same turn at the limit, but it is far better than no turn at
    all — and the Easy-Read renderer will reflow it anyway. Blocking here would
    trade a real conversation for a stylistic preference.
    """

    name: str = "readability"
    severity: Severity = Severity.WARN
    easy_read_max_words: int = 15
    standard_max_words: int = 25

    def check(self, context: GuardrailContext) -> Violation | None:
        limit = (
            self.easy_read_max_words
            if context.text_complexity == "easy_read"
            else self.standard_max_words
        )

        utterance = str(context.payload.get("npc_utterance", ""))
        longest = max((len(_words(s)) for s in _sentences(utterance)), default=0)

        if longest > limit:
            return Violation(
                check=self.name,
                severity=self.severity,
                reason=f"longest sentence is {longest} words, limit {limit}",
                repair_hint=f"Keep every sentence to {limit} words or fewer.",
            )
        return None


# ── The assembled chains ─────────────────────────────────────────────────────


def roleplay_chain() -> list:
    """Cheapest checks first, so an obviously broken payload costs least."""
    return [
        SchemaCheck(required=("npc_utterance", "npc_intent", "scenario_state")),
        ScopeCheck(),
        SafetyCheck(),
        CondescensionCheck(),
        VocabularyCheck(),
        ReadabilityCheck(),
    ]


def story_chain() -> list:
    return [
        SchemaCheck(required=("title", "panels")),
        ScopeCheck(),
        SafetyCheck(),
        CondescensionCheck(),
    ]


def interview_chain() -> list:
    """No vocabulary cage on interview questions.

    A real interview uses real language, and a learner rehearsing for one is
    entitled to rehearse against it. Scaffolding — the Easy-Read version, the
    sentence starter, the choices — is how the question is made accessible,
    rather than by making it smaller.
    """
    return [
        SchemaCheck(required=("question",)),
        ScopeCheck(),
        SafetyCheck(),
        CondescensionCheck(),
    ]


# ── Internals ────────────────────────────────────────────────────────────────


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _sentences(text: str) -> list[str]:
    return [part for part in re.split(r"[.!?]+", text) if part.strip()]


def _flatten(value, prefix: str = ""):
    """Every (key, value) pair in a nested payload.

    A patronising hint sits three levels down inside `scaffold`, and a check that
    only looked at the top level would never see it.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _flatten(item, key)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item, prefix)
    else:
        yield prefix, value

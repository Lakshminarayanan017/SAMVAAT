"""Social story generation (M10).

A social story explains a situation to someone who finds it confusing, using a
structure developed by Carol Gray and used widely in special education. The
structure is not decoration: a story that is mostly instructions reads as being
told what to do, and a story that describes and explains before it directs is
the one that actually helps.

THE RATIO IS A SCHEMA CONSTRAINT, NOT A PROMPT SUGGESTION
----------------------------------------------------------
At least two descriptive, perspective or affirmative sentences for every
directive one. Asked for in the prompt AND checked by `validate`, because a
prompt is a request. A story that fails validation is repaired once and then
falls back to the authored template — which passes the same validator, because a
fallback that failed our own structural rule would be a fallback nobody could
ship.

HUMAN IN THE LOOP
-----------------
A learner linked to a trainer gets stories as `draft` until the trainer
approves. An unlinked learner gets them immediately with a clear "AI-generated"
label. Both are honest; neither pretends a person wrote something a model did.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from guardrails.chain import GuardrailContext, run_chain
from guardrails.checks import story_chain
from providers.base import GenerationRequest, Prompt

log = logging.getLogger("samvaad.genai.stories")

SentenceType = Literal["descriptive", "perspective", "directive", "affirmative"]

#: Carol Gray's ratio. At least this many non-directive sentences per directive.
MIN_NON_DIRECTIVE_RATIO = 2.0

MIN_PANELS = 6
MAX_PANELS = 10

#: One idea per panel. Enforced by a word ceiling rather than by asking nicely,
#: because "one idea" is not a thing a validator can measure and sentence length
#: is a serviceable proxy.
MAX_WORDS_PER_PANEL = 15


STORY_PROMPT = Prompt(
    name="social_story",
    version="1.0.0",
    system=f"""You write social stories in the Carol Gray style for disabled adults preparing for \
work in India.

A social story explains a situation calmly and concretely, so that someone who finds it confusing \
knows what will happen and what they can do.

SENTENCE TYPES — you must use all four:
- descriptive: what happens, factually. "On Monday I start work at nine."
- perspective: what other people think or feel. "My supervisor is busy in the morning."
- directive:   what the learner can do. "I can say: 'Could you help me, please?'"
- affirmative: a reassuring statement of a shared value. "Asking for help is normal at work."

RULES:
- {MIN_PANELS} to {MAX_PANELS} panels, one sentence each.
- At most {MAX_WORDS_PER_PANEL} words per sentence.
- At least two descriptive, perspective or affirmative sentences for every directive one.
- Write in the first person, as the learner. "I", not "you".
- Never mention a disability unless the learner's own words did.
- Never praise the learner for effort, and never express sympathy.
- Be concrete. "I put the box on the shelf", not "I complete my responsibilities".

Respond with JSON only:
{{
  "title": "a short title",
  "panels": [{{"text": "one sentence", "type": "descriptive|perspective|directive|affirmative"}}],
  "reading_level": "easy_read"
}}""",
)


@dataclass(frozen=True)
class Panel:
    text: str
    type: SentenceType
    #: Suggested pictograph search term. The client resolves it against ARASAAC;
    #: an unresolved term renders as text alone rather than as a broken image.
    pictograph_hint: str = ""

    def as_dict(self) -> dict:
        return {"text": self.text, "type": self.type, "pictograph_hint": self.pictograph_hint}

    @property
    def word_count(self) -> int:
        return len(re.findall(r"[\w']+", self.text))


@dataclass
class ValidationResult:
    valid: bool
    problems: list[str] = field(default_factory=list)
    directive_count: int = 0
    non_directive_count: int = 0

    @property
    def ratio(self) -> float:
        return self.non_directive_count / self.directive_count if self.directive_count else 99.0

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "problems": self.problems,
            "directive_count": self.directive_count,
            "non_directive_count": self.non_directive_count,
            "ratio": round(self.ratio, 2),
        }


@dataclass
class Story:
    title: str
    panels: tuple[Panel, ...]
    status: Literal["draft", "published"]
    generated: bool
    validation: ValidationResult
    notice: str | None = None


def validate(title: str, panels: list[Panel]) -> ValidationResult:
    """The structural constraint, checked rather than requested."""
    problems: list[str] = []

    if not title.strip():
        problems.append("the story has no title")

    if not MIN_PANELS <= len(panels) <= MAX_PANELS:
        problems.append(f"{len(panels)} panels; needs {MIN_PANELS}-{MAX_PANELS}")

    directive = sum(1 for panel in panels if panel.type == "directive")
    non_directive = len(panels) - directive

    if directive == 0:
        problems.append("no directive sentence — the story never says what the learner can do")

    if directive and non_directive / directive < MIN_NON_DIRECTIVE_RATIO:
        problems.append(
            f"ratio {non_directive}:{directive} is too directive; "
            f"needs at least {MIN_NON_DIRECTIVE_RATIO:.0f}:1. A story that is mostly "
            "instructions reads as being told what to do."
        )

    if not any(panel.type == "affirmative" for panel in panels):
        problems.append("no affirmative sentence — nothing reassures the learner")

    long_panels = [panel for panel in panels if panel.word_count > MAX_WORDS_PER_PANEL]
    if long_panels:
        problems.append(
            f"{len(long_panels)} panel(s) over {MAX_WORDS_PER_PANEL} words: "
            f"{long_panels[0].text[:50]!r}"
        )

    # Quoted speech is exempt. A directive panel almost always contains one —
    # "I can say: 'Could you help me, please?'" is the single most useful
    # sentence type in a social story, and a naive second-person check rejects
    # every one of them. The rule is about who the *narration* addresses.
    second_person = [
        panel
        for panel in panels
        if re.search(r"\byou\b", _outside_quotes(panel.text), re.IGNORECASE)
    ]
    if second_person:
        problems.append(
            "a panel addresses the learner as 'you' outside quoted speech. Social "
            "stories are written in the first person, as the learner's own words "
            "about their own life."
        )

    return ValidationResult(
        valid=not problems,
        problems=problems,
        directive_count=directive,
        non_directive_count=non_directive,
    )


class StoryGenerator:
    def __init__(self, router) -> None:
        self.router = router
        self.chain = story_chain()

    def generate(
        self,
        job_context: str,
        situation: str,
        reading_level: str = "easy_read",
        has_trainer: bool = False,
    ) -> Story:
        request = GenerationRequest(
            prompt=STORY_PROMPT,
            user_message=(
                f"The learner works at: {job_context}\n"
                f"The situation to explain: {situation}\n"
                f"Reading level: {reading_level}\n\n"
                "Write the story as JSON."
            ),
            user_key="stories",
            max_tokens=900,
            temperature=0.0,
            prefill="{",
            metadata={"job_context": job_context, "situation": situation},
        )

        story = self._attempt(request, reading_level)

        if not story.validation.valid and not story.generated:
            # The authored fallback failed our own validator. That is a bug in
            # the fallback, not in the model, and it is worth being loud about:
            # it means the template we promise always works does not.
            log.error(
                "the authored story template failed validation: %s",
                "; ".join(story.validation.problems),
            )

        return Story(
            title=story.title,
            panels=story.panels,
            # A learner linked to a trainer gets a draft. Not because the story
            # is suspect, but because a special educator knowing what their
            # learner is being told is the difference between a tool an
            # institution deploys and one it blocks.
            status="draft" if has_trainer else "published",
            generated=story.generated,
            validation=story.validation,
            notice=story.notice,
        )

    def _attempt(self, request: GenerationRequest, reading_level: str) -> Story:
        generation = self.router.generate(request)
        title, panels = _parse(generation.completion.raw)

        validation = validate(title, panels)
        guardrails = run_chain(
            self.chain,
            GuardrailContext(
                payload={"title": title, "panels": [p.as_dict() for p in panels]},
                text_complexity=reading_level,
            ),
        )

        if validation.valid and guardrails.passed:
            return Story(title, tuple(panels), "published", generation.is_generated, validation)

        if generation.completion.scripted:
            # Already the fallback. Return it with its problems recorded rather
            # than looping.
            return Story(title, tuple(panels), "published", False, validation)

        log.info(
            "story rejected (%s); repairing",
            "; ".join(validation.problems + guardrails.blocked_by),
        )

        repair = GenerationRequest(
            prompt=request.prompt,
            user_message=(
                f"{request.user_message}\n\nYour previous story was rejected. Fix all of "
                "the following and return the corrected JSON only:\n- "
                + "\n- ".join(validation.problems + [v.reason for v in guardrails.violations])
            ),
            user_key=request.user_key,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            prefill=request.prefill,
            metadata=request.metadata,
        )

        generation = self.router.generate(repair)
        title, panels = _parse(generation.completion.raw)
        validation = validate(title, panels)

        if validation.valid:
            return Story(title, tuple(panels), "published", generation.is_generated, validation)

        fallback = self.router.fallback(request, "story_validation_failed")
        title, panels = _parse(fallback.completion.raw)

        return Story(
            title,
            tuple(panels),
            "published",
            False,
            validate(title, panels),
            notice=(
                "This story uses our standard wording. You can ask your trainer "
                "for a version written for you."
            ),
        )


def _outside_quotes(text: str) -> str:
    """The narration, with quoted speech removed.

    Handles straight and curly quotes, because a model produces both and a
    validator that only knows about one rejects half of what it is given.
    """
    return re.sub(r"[\"'‘’“”][^\"'‘’“”]*"
                  r"[\"'‘’“”]", " ", text)


def _parse(raw: str) -> tuple[str, list[Panel]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        try:
            payload = json.loads(raw[start : end + 1]) if start >= 0 and end > start else {}
        except json.JSONDecodeError:
            payload = {}

    panels = [
        Panel(
            text=str(item.get("text", "")).strip(),
            # An unrecognised type is treated as descriptive rather than
            # dropped: losing a panel silently changes the ratio the validator
            # then measures, and it would pass for the wrong reason.
            type=item.get("type") if item.get("type") in
            {"descriptive", "perspective", "directive", "affirmative"} else "descriptive",
            pictograph_hint=str(item.get("pictograph_hint", "")),
        )
        for item in payload.get("panels", [])
        if str(item.get("text", "")).strip()
    ]

    return str(payload.get("title", "")).strip(), panels

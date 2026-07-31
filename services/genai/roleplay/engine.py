"""The role-play engine (M9).

Turns a scenario, a learner profile and a conversation so far into the next NPC
turn — grounded in the phrase bank, guardrailed, and emitted as a `ContentBlock`
so the Modality Router decides how it looks.

    turn request
      -> build context: profile + scenario state + error signature + target phrases
      -> retrieve: top-k phrases, filtered by tags and the ZPD difficulty window
      -> generate: versioned prompt, schema-constrained, temperature 0
      -> guardrail chain
      -> on failure: repair-retry once, then a scripted turn
      -> emit ContentBlock(kind='scenario_turn')

THE PAYOFF
----------
`scaffold.choices` is what makes one generated turn work for five people. The
same turn is free-form conversation for P1, a three-choice tap for P4, captions
plus ISL for P2, and a switch-scannable list for P3. One generation, five
renderings — this is the Modality Router earning its keep.

DIFFICULTY ADAPTATION
---------------------
Target success rate 70-80%, the Zone of Proximal Development. The levers are
vocabulary tier, sentence length, turn length, scaffold availability, and how
patient the NPC is.

Never speed. Never a timer. Ethics E6 is not a UI rule — it is a rule about what
difficulty is allowed to mean, and it is enforced here by the fact that
`Difficulty` has no time field for anything to read.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace

from guardrails.chain import GuardrailContext, GuardrailReport, run_chain
from guardrails.checks import roleplay_chain
from providers.base import GenerationRequest, Prompt
from retrieval.index import Query, load_index
from roleplay import scenarios

log = logging.getLogger("samvaad.genai.roleplay")

#: Success rate the difficulty adapter aims for. Below it, the learner is
#: failing more than they are learning; above it, they are not being stretched.
ZPD_TARGET_LOW = 0.70
ZPD_TARGET_HIGH = 0.80

#: Turns of history sent to the model. Enough for coherence, short enough that
#: cost does not grow linearly with conversation length.
HISTORY_TURNS = 6

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5


ROLEPLAY_PROMPT = Prompt(
    name="roleplay_turn",
    version="1.0.0",
    system="""You play a colleague in a workplace role-play for an app that helps disabled adults \
practise workplace communication in India.

You are talking to a competent adult colleague. Be warm and ordinary — exactly as you would be \
with anyone else at work.

NEVER:
- praise the learner for effort alone ("well done for trying")
- mention, refer to, or accommodate a disability unless the learner raises it first
- offer to slow down, simplify, or check whether they understood
- express sympathy, admiration, or surprise at their being there
- leave the workplace scenario

ALWAYS:
- stay in character and in the scenario
- hand the conversation back so the learner has something to say
- use phrases from the provided bank as `target_phrases` when they fit naturally
- keep `npc_utterance` to at most three sentences

Respond with JSON only, matching this shape exactly:
{
  "npc_utterance": "what you say",
  "npc_intent": "one of: greet, request_information, request_status, offer_help, acknowledge, \
agree, disagree, repeat, reassure, close",
  "expected_learner_intents": ["what a good reply would do"],
  "target_phrases": ["phrase ids from the bank, or []"],
  "difficulty_delta": -1 | 0 | 1,
  "scaffold": {
    "hint": "one short sentence telling the learner what they could say",
    "sentence_starter": "the first two or three words of a good reply",
    "choices": ["three complete replies the learner could pick"]
  },
  "easy_read_version": "the same turn, one idea per line, sentences of at most 15 words",
  "scenario_state": {"turn": 0, "goal_met": false}
}""",
)


@dataclass(frozen=True)
class Turn:
    """One exchange in the transcript."""

    speaker: str  # 'npc' | 'learner'
    text: str


@dataclass
class ConversationState:
    """Everything that persists between turns.

    Held by the caller and passed in, so the engine is stateless and a
    conversation survives a redeploy mid-sentence.
    """

    scenario_id: str
    difficulty: int = 2
    turn_number: int = 0
    history: list[Turn] = field(default_factory=list)
    #: Rolling record of whether the learner's replies met expectations. Drives
    #: the ZPD adjustment. Bounded, so a good day three weeks ago does not keep
    #: a learner pinned at a level they have stopped managing.
    outcomes: list[bool] = field(default_factory=list)
    #: Intents the learner has recently struggled with; boosts retrieval.
    error_signature: tuple[str, ...] = ()
    goal_met: bool = False
    persona: str = "supportive"

    @property
    def success_rate(self) -> float | None:
        recent = self.outcomes[-10:]
        return sum(recent) / len(recent) if len(recent) >= 4 else None


@dataclass(frozen=True)
class TurnResult:
    """A generated turn, ready to become a ContentBlock."""

    block: dict
    state: ConversationState
    guardrails: GuardrailReport
    #: True when a model produced this. The client labels AI content honestly.
    generated: bool
    provider: str
    prompt_id: str
    retrieved_ids: tuple[str, ...] = ()
    repaired: bool = False


class RolePlayEngine:
    def __init__(self, router, index=None) -> None:
        self.router = router
        self.index = index or load_index()
        self.chain = roleplay_chain()

    # ── public ───────────────────────────────────────────────────────────────

    def open(self, scenario_id: str, difficulty: int = 2, persona: str = "supportive") -> TurnResult:
        """The first turn.

        Authored, never generated. The opening line sets the whole frame, it is
        the same every time so a learner returning to a scenario recognises it,
        and it costs nothing.
        """
        scenario = self._scenario(scenario_id)

        state = ConversationState(
            scenario_id=scenario_id,
            difficulty=_clamp_difficulty(difficulty),
            persona=persona if persona in scenarios.PERSONAS else "supportive",
        )

        payload = {
            "npc_utterance": scenario.opening,
            "npc_intent": "greet",
            "expected_learner_intents": ["respond"],
            "target_phrases": [],
            "difficulty_delta": 0,
            "scaffold": {
                "hint": "Answer in your own words, or pick one below.",
                "sentence_starter": "",
                "choices": _opening_choices(scenario),
            },
            "easy_read_version": scenario.opening_easy_read or scenario.opening,
            "scenario_state": {"turn": 0, "goal_met": False},
        }

        state.history.append(Turn(speaker="npc", text=scenario.opening))

        return TurnResult(
            block=self._to_content_block(payload, state, scenario),
            state=state,
            guardrails=GuardrailReport(),
            generated=False,
            provider="authored",
            prompt_id="authored/opening",
        )

    def respond(self, state: ConversationState, learner_text: str, met_expectation: bool) -> TurnResult:
        """The next NPC turn, after the learner has said something."""
        scenario = self._scenario(state.scenario_id)

        state = replace(
            state,
            turn_number=state.turn_number + 1,
            history=[*state.history, Turn(speaker="learner", text=learner_text)],
            outcomes=[*state.outcomes, met_expectation],
        )

        retrieved = self.index.search(
            Query(
                text=learner_text or scenario.goal,
                scenario_tags=scenario.scenario_tags,
                min_difficulty=max(MIN_DIFFICULTY, state.difficulty - 1),
                # One tier above current: the Zone of Proximal Development, in
                # a filter rather than in a prompt instruction the model may
                # decide to ignore.
                max_difficulty=min(MAX_DIFFICULTY, state.difficulty + 1),
                error_signature=state.error_signature,
            )
        )

        request = GenerationRequest(
            prompt=ROLEPLAY_PROMPT,
            user_message=self._build_context(scenario, state, retrieved),
            user_key=_budget_key(state),
            max_tokens=600,
            temperature=0.0,
            prefill="{",
            metadata={
                "scenario": {
                    "scripted_turns": [dict(t) for t in scenario.scripted_turns],
                    "target_phrases": [r.block_id for r in retrieved[:3]],
                },
                "scenario_state": {"turn": state.turn_number, "goal_met": state.goal_met},
            },
        )

        payload, report, generation, repaired = self._generate_checked(request, scenario, state)

        state = replace(
            state,
            difficulty=self._next_difficulty(state, payload.get("difficulty_delta", 0)),
            goal_met=bool(payload.get("scenario_state", {}).get("goal_met", state.goal_met)),
            history=[*state.history, Turn(speaker="npc", text=payload["npc_utterance"])],
        )

        return TurnResult(
            block=self._to_content_block(payload, state, scenario),
            state=state,
            guardrails=report,
            generated=generation.is_generated,
            provider=generation.provider,
            prompt_id=generation.completion.prompt_id,
            retrieved_ids=tuple(r.block_id for r in retrieved),
            repaired=repaired,
        )

    # ── generation with the guardrail chain ──────────────────────────────────

    def _generate_checked(self, request, scenario, state):
        """Generate, check, repair once, then fall back.

        The repair sends a *different* message — the model is told exactly what
        broke. Re-sending the identical request at temperature 0 would produce
        the identical rejected answer, which is a well-intentioned way to pay
        twice for the same failure.
        """
        generation = self.router.generate(request)
        payload = self._parse(generation.completion.raw)

        # Authored content skips the chain entirely. A person wrote it, a person
        # reviewed it, and running the checks anyway produces a report saying
        # `passed: false` about content we are serving regardless — which is
        # worse than no report, because it teaches everyone to ignore the field.
        if generation.completion.scripted:
            return self._ground(payload, scenario), GuardrailReport(), generation, False

        context = GuardrailContext(
            payload=payload,
            difficulty=state.difficulty,
            text_complexity=request.metadata.get("text_complexity", "standard"),
            allowed_phrase_ids=self.index.known_ids(),
            scenario_terms=scenario.allowed_terms,
            scenario_setting=scenario.setting,
        )
        report = run_chain(self.chain, context)

        if report.passed:
            return self._ground(payload, scenario), report, generation, False

        log.info("guardrails blocked a turn (%s); repairing", ", ".join(report.blocked_by))

        repair = replace(
            request,
            user_message=f"{request.user_message}\n\n{report.repair_instructions()}",
        )
        generation = self.router.generate(repair)
        payload = self._parse(generation.completion.raw)

        report = run_chain(self.chain, replace(context, payload=payload))

        if report.passed:
            return self._ground(payload, scenario), report, generation, True

        # Still failing. Authored content, which is guaranteed to pass because
        # a person wrote it. The learner sees a slightly less interesting
        # conversation and nothing else.
        log.warning("guardrails blocked the repair too (%s); serving authored", report.blocked_by)

        scripted = self.router.fallback(request, "guardrails_blocked")
        return (
            self._ground(self._parse(scripted.completion.raw), scenario),
            report,
            scripted,
            True,
        )

    def _parse(self, raw: str) -> dict:
        """Parse the model's JSON, defensively.

        A malformed payload becomes an empty dict, which the schema check then
        blocks — rather than an exception three frames up that ends a learner's
        conversation.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Models occasionally wrap JSON in prose despite the prefill.
            start, end = raw.find("{"), raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    pass

            log.warning("could not parse a generation as JSON")
            return {}

    def _ground(self, payload: dict, scenario) -> dict:
        """Drop any phrase id that is not in our bank.

        The grounding guarantee, enforced rather than requested. A hallucinated
        id renders as a broken reference in the client and, worse, tells the
        learner we teach a phrase we do not.
        """
        known = self.index.known_ids()
        cited = payload.get("target_phrases") or []

        kept = [phrase_id for phrase_id in cited if phrase_id in known]

        if len(kept) != len(cited):
            log.info("dropped %d ungrounded phrase ids", len(cited) - len(kept))

        payload["target_phrases"] = kept
        return payload

    # ── difficulty ───────────────────────────────────────────────────────────

    def _next_difficulty(self, state: ConversationState, model_delta: int) -> int:
        """Adjust toward the ZPD band.

        The measured success rate outranks the model's own suggestion. The model
        sees one turn; the success rate sees the conversation, and it is the
        quantity the target is actually defined over.
        """
        rate = state.success_rate

        if rate is None:
            return _clamp_difficulty(state.difficulty + _clamp_delta(model_delta))

        if rate > ZPD_TARGET_HIGH:
            return _clamp_difficulty(state.difficulty + 1)
        if rate < ZPD_TARGET_LOW:
            return _clamp_difficulty(state.difficulty - 1)

        return state.difficulty

    # ── context and output ───────────────────────────────────────────────────

    def _build_context(self, scenario, state: ConversationState, retrieved) -> str:
        history = "\n".join(
            f"{'You' if turn.speaker == 'npc' else 'Learner'}: {turn.text}"
            for turn in state.history[-HISTORY_TURNS:]
        )

        phrases = "\n".join(r.as_context_line() for r in retrieved)

        return (
            f"{scenario.as_context()}\n"
            f"Your manner: {_persona_description(state.persona)}\n"
            f"Difficulty tier: {state.difficulty} of 5\n\n"
            f"Phrases from the learner's bank you may steer toward:\n{phrases}\n\n"
            f"Conversation so far:\n{history}\n\n"
            "Give your next turn as JSON."
        )

    def _to_content_block(self, payload: dict, state: ConversationState, scenario) -> dict:
        """A ContentBlock, so the Modality Router renders it.

        Note what is absent: any decision about how this looks. The engine emits
        meaning and representations; the client's router picks the channel from
        the learner's profile. That is the whole architecture in one function.
        """
        return {
            "id": f"scenario.{scenario.id}.turn_{state.turn_number}",
            "kind": "scenario_turn",
            "canonical_text": payload["npc_utterance"],
            "intent": payload.get("npc_intent", "acknowledge"),
            "difficulty": state.difficulty,
            "scenario_tags": list(scenario.scenario_tags),
            "representations": {
                "caption": payload["npc_utterance"],
                "easy_read": payload.get("easy_read_version") or payload["npc_utterance"],
            },
            "interaction": {
                "accepted_input_modes": ["speech", "text", "aac", "sign", "switch"],
                "target_response": {"type": "open_response"},
                "hints": [payload.get("scaffold", {}).get("hint", "")],
                # The line that makes one generation serve five people.
                "choices": payload.get("scaffold", {}).get("choices", []),
                "sentence_starter": payload.get("scaffold", {}).get("sentence_starter", ""),
                "target_phrases": payload.get("target_phrases", []),
            },
            "a11y": {
                "requires_audio": False,
                "requires_vision": False,
                "requires_speech": False,
            },
            "version": 1,
            "source": "generated",
        }

    def _scenario(self, scenario_id: str):
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            raise KeyError(
                f"Unknown scenario '{scenario_id}'. Known: {', '.join(scenarios.scenario_ids())}"
            )
        return scenario


# ── helpers ──────────────────────────────────────────────────────────────────


def _clamp_difficulty(value: int) -> int:
    return max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, value))


def _clamp_delta(value) -> int:
    try:
        return max(-1, min(1, int(value)))
    except (TypeError, ValueError):
        return 0


def _budget_key(state: ConversationState) -> str:
    """An opaque budget key. The provider layer counts spend without needing to
    know who the learner is."""
    return f"roleplay:{state.scenario_id}"


def _persona_description(persona: str) -> str:
    return {
        "supportive": "friendly and encouraging, without being effusive",
        "neutral": "professional and matter-of-fact",
        # Brisk means short sentences and less patience for digression. It does
        # NOT mean hurrying the learner, and there is no timer anywhere.
        "brisk": "busy and direct, with short sentences — never rude, never rushing them",
    }.get(persona, "friendly and encouraging")


def _opening_choices(scenario) -> list[str]:
    """Three replies for the opening turn.

    Taken from the scenario's own first scripted turn where it has one, so a
    learner who needs choices gets scenario-specific ones rather than generic
    filler.
    """
    if scenario.scripted_turns:
        choices = scenario.scripted_turns[0].get("choices")
        if choices:
            return list(choices)
    return []

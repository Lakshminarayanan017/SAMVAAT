"""The scripted provider — the product with no API key at all.

NOT A MOCK. This is a first-class path that must work well, for four reasons:

  1. **Outages.** When the LLM is unreachable, a learner mid-interview gets the
     rest of their interview rather than an error screen. Role-play degrades to
     an authored branch and keeps going.
  2. **Cost.** A learner who has exhausted their daily token budget continues to
     use the product. The budget limits generation, not access.
  3. **CI.** The full role-play and interview flows run on every build with no
     key and no network. A path that only runs in production is a path that
     breaks in production.
  4. **Offline.** M15 caches scripted turns so a role-play works on a bus.

Everything here is authored text, and the service labels it as such: the client
shows "AI-generated" only when a model was actually involved. Telling a learner
that a human-written sentence came from an AI, or the reverse, is a small lie
that costs trust disproportionately.

DETERMINISM
-----------
Selection is by hash of the request, not by random choice. The same context
always produces the same turn, so a learner who repeats a scenario gets a
coherent experience, and a test asserting on a scripted turn does not flake.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable

from providers.base import Completion, GenerationRequest, LLMError, LLMProvider

log = logging.getLogger("samvaad.genai.scripted")

#: prompt name -> a function producing a schema-valid payload for that prompt.
#: Registered rather than hard-coded in one function so a new generative feature
#: cannot ship without someone deciding what it does when the model is absent.
_RESPONDERS: dict[str, Callable[[GenerationRequest], dict]] = {}


def responder(prompt_name: str):
    """Register the authored fallback for one prompt."""

    def register(function: Callable[[GenerationRequest], dict]):
        _RESPONDERS[prompt_name] = function
        return function

    return register


def registered_prompts() -> frozenset[str]:
    """Every prompt that has an authored fallback.

    Asserted against the prompt registry by a test: a generative feature with no
    scripted path is a feature that disappears during an outage, and the moment
    to discover that is a build, not an incident.
    """
    return frozenset(_RESPONDERS)


class ScriptedProvider(LLMProvider):
    name = "scripted"
    is_generative = False

    def complete(self, request: GenerationRequest) -> Completion:
        build = _RESPONDERS.get(request.prompt.name)

        if build is None:
            raise LLMError(
                f"No scripted fallback registered for prompt '{request.prompt.name}'. "
                "Every generative feature needs one — see providers/scripted.py.",
                retryable=False,
            )

        payload = build(request)

        return Completion(
            raw=json.dumps(payload),
            model="scripted",
            prompt_id=request.prompt.id,
            scripted=True,
        )


def choose(options: list, request: GenerationRequest):
    """Pick deterministically from authored options.

    Hashing the request rather than sampling: the same situation produces the
    same reply, which is what makes a scripted conversation coherent when a
    learner backtracks, and what stops tests flaking.
    """
    digest = hashlib.sha256(request.cache_key().encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


# ── Role-play (M9) ───────────────────────────────────────────────────────────


@responder("roleplay_turn")
def _roleplay_turn(request: GenerationRequest) -> dict:
    """An authored NPC turn.

    The scenario supplies its own scripted branches wherever it can — an authored
    line written for *this* scenario beats a generic one. These generic turns are
    the floor beneath that: they keep a conversation moving and hand control back
    to the learner, which is the one thing a stuck role-play must do.
    """
    scenario = request.metadata.get("scenario", {})
    branches = scenario.get("scripted_turns") or []

    if branches:
        turn = choose(branches, request)
    else:
        turn = choose(_GENERIC_TURNS, request)

    target_phrases = list(scenario.get("target_phrases", []))[:3]

    return {
        "npc_utterance": turn["utterance"],
        "npc_intent": turn.get("intent", "acknowledge"),
        "expected_learner_intents": turn.get("expects", ["respond"]),
        "target_phrases": target_phrases,
        # Scripted turns never change difficulty. Adaptation is a judgement
        # about the learner, and an authored line has not made one.
        "difficulty_delta": 0,
        "scaffold": {
            "hint": turn.get("hint", "You can answer in your own words."),
            "sentence_starter": turn.get("starter", ""),
            "choices": turn.get("choices", []),
        },
        "easy_read_version": turn.get("easy_read", turn["utterance"]),
        "scenario_state": request.metadata.get("scenario_state", {}),
    }


#: Deliberately open-ended and unhurried. Each hands the turn back to the learner
#: without demanding a specific answer, so any of them is a reasonable thing to
#: hear at almost any point in a workplace conversation.
_GENERIC_TURNS: list[dict] = [
    {
        "utterance": "Thanks for letting me know. Is there anything you need from me?",
        "intent": "offer_help",
        "expects": ["request_help", "decline_politely"],
        "hint": "You could ask for something you need, or say you are fine.",
        "starter": "Could you",
        "choices": ["Could you show me once more?", "No thank you, I am fine.", "I need more time."],
        "easy_read": "Thank you for telling me.\nDo you need anything?",
    },
    {
        "utterance": "That sounds good. How is it going so far?",
        "intent": "request_status",
        "expects": ["report_progress"],
        "hint": "Tell them how far you have got.",
        "starter": "I have finished",
        "choices": ["I have finished the first batch.", "I am about halfway.", "I am running late."],
        "easy_read": "Good.\nHow is your work going?",
    },
    {
        "utterance": "No problem at all. Take the time you need.",
        "intent": "reassure",
        "expects": ["thank", "continue"],
        "hint": "You could say thank you, or carry on.",
        "starter": "Thank you",
        "choices": ["Thank you.", "I will finish it today.", "Could I have some help?"],
        "easy_read": "That is fine.\nTake your time.",
    },
    {
        "utterance": "Of course. Let me say that again more slowly.",
        "intent": "repeat",
        "expects": ["acknowledge", "request_clarification"],
        "hint": "You can say thank you, or ask again if it is still unclear.",
        "starter": "Thank you",
        "choices": ["Thank you.", "Could you write it down?", "I understand now."],
        "easy_read": "Yes.\nI will say it again.\nI will speak slowly.",
    },
]


# ── Social stories (M10) ─────────────────────────────────────────────────────


@responder("social_story")
def _social_story(request: GenerationRequest) -> dict:
    """A structurally valid story built from the learner's own job context.

    Follows the Carol Gray ratio — at least two descriptive or perspective
    sentences for every directive one — because the structural validator is the
    same for scripted and generated stories. A fallback that failed our own
    validator would be a fallback nobody could ship.
    """
    context = request.metadata.get("job_context") or "my workplace"
    situation = request.metadata.get("situation") or "asking my supervisor a question"

    return {
        "title": f"Asking a question at {context}",
        "panels": [
            {"text": f"I work at {context}.", "type": "descriptive"},
            {"text": "Sometimes I am not sure what to do next.", "type": "descriptive"},
            {"text": "That is normal. Many people ask questions at work.", "type": "perspective"},
            {"text": f"When I am unsure about {situation}, I can ask.", "type": "directive"},
            {"text": "I can say: \"Could you help me, please?\"", "type": "directive"},
            {"text": "My supervisor is happy to explain again.", "type": "perspective"},
            {"text": "Asking a question helps me do my job well.", "type": "affirmative"},
        ],
        "reading_level": "easy_read",
    }


# ── Interview (M11) ──────────────────────────────────────────────────────────


@responder("interview_question")
def _interview_question(request: GenerationRequest) -> dict:
    """An authored interview question.

    A mock interview must never stop half way. A learner who has worked up to
    doing this deserves to finish it, and an outage is not their problem.
    """
    track = request.metadata.get("track", "hr")
    asked = set(request.metadata.get("asked_question_ids", []))

    pool = [q for q in _INTERVIEW_QUESTIONS.get(track, _INTERVIEW_QUESTIONS["hr"])
            if q["id"] not in asked]

    if not pool:
        return {"question": None, "question_id": None, "is_final": True, "follow_up_to": None}

    question = choose(pool, request)

    return {
        "question": question["text"],
        "question_id": question["id"],
        "easy_read_version": question["easy_read"],
        "is_final": len(pool) == 1,
        "follow_up_to": None,
        "scaffold": {
            "hint": question.get("hint", "Take your time. There is no rush."),
            "sentence_starter": question.get("starter", ""),
            "choices": [],
        },
    }


_INTERVIEW_QUESTIONS: dict[str, list[dict]] = {
    "hr": [
        {
            "id": "hr.tell_me_about_yourself",
            "text": "Tell me a little about yourself.",
            "easy_read": "Tell me about you.\nWhat work do you like?",
            "starter": "My name is",
        },
        {
            "id": "hr.strength",
            "text": "What would you say is your biggest strength?",
            "easy_read": "What are you good at?",
            "starter": "I am good at",
        },
        {
            "id": "hr.difficult_situation",
            "text": "Tell me about a time something at work was difficult. What did you do?",
            "easy_read": "Tell me about a hard day at work.\nWhat did you do?",
            "starter": "One time,",
        },
        {
            "id": "hr.why_this_role",
            "text": "Why are you interested in this role?",
            "easy_read": "Why do you want this job?",
            "starter": "I want this job because",
        },
        {
            "id": "hr.support",
            "text": "Is there anything that would help you do your best work here?",
            "easy_read": "What would help you at work?",
            "starter": "It helps me if",
        },
    ],
    "role": [
        {
            "id": "role.experience",
            "text": "What experience do you have that fits this job?",
            "easy_read": "What work have you done before?",
            "starter": "I have worked",
        },
        {
            "id": "role.safety",
            "text": "If you saw something unsafe at work, what would you do?",
            "easy_read": "You see something unsafe.\nWhat do you do?",
            "starter": "I would tell",
        },
        {
            "id": "role.instructions",
            "text": "How do you like to be given instructions?",
            "easy_read": "How do you like to learn a new job?",
            "starter": "It helps me if",
        },
    ],
    "telephonic": [
        {
            "id": "tel.introduce",
            "text": "Good morning. Could you introduce yourself, please?",
            "easy_read": "Good morning.\nPlease tell me your name.",
            "starter": "Good morning, my name is",
        },
        {
            "id": "tel.availability",
            "text": "When would you be able to start?",
            "easy_read": "When can you start work?",
            "starter": "I can start",
        },
        {
            "id": "tel.repeat",
            "text": "Sorry, the line is not very clear. Could you say that once more?",
            "easy_read": "I cannot hear you well.\nPlease say it again.",
            "starter": "",
        },
    ],
}


# ── Rubric (M11) ─────────────────────────────────────────────────────────────


@responder("rubric_score")
def _rubric_score(request: GenerationRequest) -> dict:
    """The one scripted responder that refuses to do its job, on purpose.

    An interview score is a judgement about a person's employability. Inventing
    one from authored text — however plausible it looked — would put a fabricated
    assessment in front of a learner and into an audit record that claims to be
    reviewable. There is no honest scripted rubric.

    So the interview still completes, the transcript is still saved, and the
    learner is told plainly that scoring will follow. `scored: false` is what the
    API checks; it never persists a rubric row from this.
    """
    return {
        "scored": False,
        "reason": "scoring_unavailable",
        "message": (
            "Your interview is saved. The detailed feedback needs a connection, "
            "and it will be here when you come back."
        ),
    }

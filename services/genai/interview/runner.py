"""The mock interview (M11).

Three tracks, adaptive follow-ups, pause and resume at any point, and a
transcript the learner can replay. The scoring lives in `rubric/`; this module
is about running the conversation well.

WHAT MAKES THIS DIFFERENT FROM A QUESTION LIST
-----------------------------------------------
**Pause and resume is a first-class feature, not a nicety.** A learner with
anxiety, with a stammer, or with fatigue may need to stop mid-answer and come
back tomorrow. An interview that cannot be paused is an interview P4 and P5 will
not finish, and an unfinished interview produces no feedback at all. State is
serialisable and the caller owns it, so stopping costs nothing.

**Every track runs in every modality.** A text-only interview for a non-verbal
learner is a first-class path, not a fallback: the questions are ContentBlocks
and the Modality Router decides how they arrive. `telephonic` is audio-only by
design — it is deliberately the hardest track because real telephone interviews
strip away every visual cue — but even it accepts typed answers, because the
skill being practised is answering without visual context, not speaking.

**The interviewer persona is chosen by the learner**, and `supportive` is the
default. Somebody meeting this feature for the first time should meet the kind
version of it.

NO TIMERS. ANYWHERE.
--------------------
There is no per-question time limit, no total duration, and no "you are taking
a while" prompt. `InterviewState` has no time field for anything to read, which
is how Ethics E6 is enforced rather than merely intended.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Literal

from guardrails.chain import GuardrailContext, run_chain
from guardrails.checks import interview_chain
from providers.base import GenerationRequest, Prompt

log = logging.getLogger("samvaad.genai.interview")

Track = Literal["hr", "role", "telephonic"]
TRACKS: tuple[Track, ...] = ("hr", "role", "telephonic")

#: Questions per interview. The lower bound is what makes the rubric meaningful;
#: the upper bound is what stops it becoming an endurance test.
MIN_QUESTIONS = 8
MAX_QUESTIONS = 12

#: A follow-up is asked when an answer is short enough that there is obviously
#: more to say. Measured in words, and deliberately generous — a four-word answer
#: from an AAC user may be complete, so this triggers a gentle invitation and
#: never a demand.
FOLLOW_UP_WORD_THRESHOLD = 12

#: At most one follow-up per question. Two is an interrogation.
MAX_FOLLOW_UPS_PER_QUESTION = 1


QUESTION_PROMPT = Prompt(
    name="interview_question",
    version="1.0.0",
    system="""You are an interviewer in a mock job interview for an app that helps disabled adults \
in India prepare for real interviews.

Ask ONE question at a time. You are interviewing a competent adult candidate — be professional and \
ordinary, exactly as you would with anyone.

NEVER:
- praise the candidate for effort, attendance, or bravery
- mention or ask about a disability unless they raised it first
- offer to slow down, simplify, or check whether they understood
- ask more than one question in a turn
- refer to how long they took, or to how they spoke

If the previous answer was brief, you may ask ONE gentle follow-up inviting more detail — phrased \
as interest, never as a complaint that the answer was insufficient.

Respond with JSON only:
{
  "question": "the question you ask",
  "question_id": "a short stable slug",
  "easy_read_version": "the same question, at most 15 words, one idea per line",
  "is_final": false,
  "follow_up_to": null,
  "scaffold": {
    "hint": "one sentence about what a good answer might cover",
    "sentence_starter": "the first two or three words of a possible answer",
    "choices": []
  }
}""",
)


@dataclass(frozen=True)
class Exchange:
    """One question and its answer."""

    question_id: str
    question: str
    answer: str = ""
    is_follow_up: bool = False
    #: Set once the rubric has scored it. Kept on the exchange so a paused
    #: interview resumes with its partial feedback intact.
    scored: bool = False

    @property
    def answered(self) -> bool:
        return bool(self.answer.strip())


@dataclass
class InterviewState:
    """The whole interview, serialisable.

    Note what is absent: any timestamp of when a question was asked or answered,
    any duration, any per-question clock. Ethics E6 is enforced by the shape of
    this object — nothing downstream can score response latency because nothing
    records it.

    `started_at` exists only so a learner sees "you began this on Tuesday" when
    resuming. It is never per-question, and it never reaches the rubric.
    """

    interview_id: str
    track: Track = "hr"
    persona: str = "supportive"
    exchanges: list[Exchange] = field(default_factory=list)
    target_questions: int = 10
    status: Literal["in_progress", "paused", "complete"] = "in_progress"
    started_at: str = ""
    job_context: str = ""

    @property
    def asked_question_ids(self) -> list[str]:
        return [exchange.question_id for exchange in self.exchanges]

    @property
    def answered_count(self) -> int:
        return sum(1 for exchange in self.exchanges if exchange.answered)

    @property
    def is_complete(self) -> bool:
        return self.answered_count >= self.target_questions

    @property
    def follow_ups_for_current(self) -> int:
        """How many follow-ups the most recent real question has already had."""
        count = 0
        for exchange in reversed(self.exchanges):
            if exchange.is_follow_up:
                count += 1
            else:
                break
        return count

    def progress_message(self) -> str:
        """Progress, never pressure.

        Says how far through, never how long it has taken and never how long is
        left in time. "Four of ten" is orientation; "six minutes remaining" is a
        countdown, and a countdown is the fastest way to make this unusable for
        three of our five personas.
        """
        if self.status == "complete":
            return "That is the whole interview. Well done for finishing it."
        return f"Question {self.answered_count + 1} of about {self.target_questions}."


@dataclass(frozen=True)
class QuestionResult:
    block: dict
    state: InterviewState
    generated: bool
    provider: str
    finished: bool = False


class InterviewRunner:
    def __init__(self, router, index=None) -> None:
        self.router = router
        self.index = index
        self.chain = interview_chain()

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(
        self,
        interview_id: str,
        track: Track = "hr",
        persona: str = "supportive",
        target_questions: int = 10,
        job_context: str = "",
    ) -> InterviewState:
        if track not in TRACKS:
            raise ValueError(f"Unknown track '{track}'; choose from {', '.join(TRACKS)}")

        return InterviewState(
            interview_id=interview_id,
            track=track,
            persona=persona,
            target_questions=max(MIN_QUESTIONS, min(MAX_QUESTIONS, target_questions)),
            started_at=datetime.now(timezone.utc).isoformat(),
            job_context=job_context,
        )

    def pause(self, state: InterviewState) -> InterviewState:
        """Stop wherever the learner is.

        No penalty, no expiry, no warning. The state is returned to the caller
        and can be stored for as long as the learner needs.
        """
        return replace(state, status="paused")

    def resume(self, state: InterviewState) -> InterviewState:
        return replace(state, status="in_progress")

    # ── the conversation ─────────────────────────────────────────────────────

    def next_question(self, state: InterviewState) -> QuestionResult:
        """The next question, or the end of the interview."""
        if state.is_complete:
            return QuestionResult(
                block=self._closing_block(state),
                state=replace(state, status="complete"),
                generated=False,
                provider="authored",
                finished=True,
            )

        wants_follow_up = self._should_follow_up(state)

        request = GenerationRequest(
            prompt=QUESTION_PROMPT,
            user_message=self._build_context(state, wants_follow_up),
            user_key=f"interview:{state.track}",
            max_tokens=400,
            temperature=0.0,
            prefill="{",
            metadata={
                "track": state.track,
                "asked_question_ids": state.asked_question_ids,
            },
        )

        payload, generation = self._generate_checked(request, state)

        if not payload.get("question"):
            # The authored pool is exhausted. Ending here is correct: an
            # interview that runs out of questions and starts repeating them is
            # worse than a slightly shorter one.
            return QuestionResult(
                block=self._closing_block(state),
                state=replace(state, status="complete"),
                generated=False,
                provider=generation.provider,
                finished=True,
            )

        question_id = str(payload.get("question_id") or f"q{len(state.exchanges)}")

        state = replace(
            state,
            exchanges=[
                *state.exchanges,
                Exchange(
                    question_id=question_id,
                    question=payload["question"],
                    is_follow_up=wants_follow_up,
                ),
            ],
        )

        return QuestionResult(
            block=self._to_content_block(payload, state, question_id),
            state=state,
            generated=generation.is_generated,
            provider=generation.provider,
        )

    def record_answer(self, state: InterviewState, answer: str) -> InterviewState:
        """Attach an answer to the question currently on screen.

        Answers are recorded verbatim. The rubric receives a scrubbed copy; the
        learner's own words are kept intact so they can replay exactly what they
        said, which is the whole point of the transcript.
        """
        if not state.exchanges:
            raise ValueError("No question has been asked yet")

        exchanges = list(state.exchanges)
        exchanges[-1] = replace(exchanges[-1], answer=answer)

        updated = replace(state, exchanges=exchanges)

        if updated.is_complete:
            updated = replace(updated, status="complete")

        return updated

    # ── internals ────────────────────────────────────────────────────────────

    def _should_follow_up(self, state: InterviewState) -> bool:
        """A brief answer invites one gentle follow-up.

        Never two, and never phrased as a complaint. A four-word answer from an
        AAC user may be complete and correct — the follow-up is an invitation to
        say more, which they are free to decline.
        """
        if not state.exchanges:
            return False

        last = state.exchanges[-1]

        if not last.answered:
            return False
        if state.follow_ups_for_current >= MAX_FOLLOW_UPS_PER_QUESTION:
            return False

        return len(last.answer.split()) < FOLLOW_UP_WORD_THRESHOLD

    def _generate_checked(self, request: GenerationRequest, state: InterviewState):
        generation = self.router.generate(request)
        payload = _parse(generation.completion.raw)

        if generation.completion.scripted:
            return payload, generation

        report = run_chain(
            self.chain,
            GuardrailContext(payload=payload, difficulty=3, scenario_setting="interview"),
        )

        if report.passed:
            return payload, generation

        log.info("guardrails blocked an interview question (%s)", ", ".join(report.blocked_by))

        # One repair, then authored. A learner who has worked up to doing a mock
        # interview deserves to finish it; a guardrail argument is not their
        # problem.
        repair = replace(
            request,
            user_message=f"{request.user_message}\n\n{report.repair_instructions()}",
        )
        generation = self.router.generate(repair)
        payload = _parse(generation.completion.raw)

        if run_chain(self.chain, GuardrailContext(payload=payload, difficulty=3)).passed:
            return payload, generation

        fallback = self.router.fallback(request, "guardrails_blocked")
        return _parse(fallback.completion.raw), fallback

    def _build_context(self, state: InterviewState, wants_follow_up: bool) -> str:
        transcript = "\n".join(
            f"Q: {exchange.question}\nA: {exchange.answer or '(not yet answered)'}"
            for exchange in state.exchanges[-3:]
        )

        instruction = (
            "Ask ONE gentle follow-up to their last answer, inviting more detail."
            if wants_follow_up
            else "Ask the next question."
        )

        return (
            f"Track: {_track_description(state.track)}\n"
            f"Your manner: {_persona_description(state.persona)}\n"
            f"{f'The role: {state.job_context}{chr(10)}' if state.job_context else ''}"
            f"Question {state.answered_count + 1} of about {state.target_questions}.\n\n"
            f"So far:\n{transcript or '(the interview has not started)'}\n\n"
            f"{instruction} Respond as JSON."
        )

    def _to_content_block(self, payload: dict, state: InterviewState, question_id: str) -> dict:
        return {
            "id": f"interview.{state.track}.{question_id}",
            "kind": "interview_question",
            "canonical_text": payload["question"],
            "intent": "interview_question",
            "difficulty": 3,
            "scenario_tags": ["interview", state.track],
            "representations": {
                "caption": payload["question"],
                "easy_read": payload.get("easy_read_version") or payload["question"],
            },
            "interaction": {
                # Every track accepts every input mode. A text-only interview for
                # a non-verbal learner is a first-class path, not a fallback.
                "accepted_input_modes": ["speech", "text", "aac", "sign", "switch"],
                "target_response": {"type": "open_response"},
                "hints": [payload.get("scaffold", {}).get("hint", "")],
                "sentence_starter": payload.get("scaffold", {}).get("sentence_starter", ""),
                "choices": payload.get("scaffold", {}).get("choices", []),
            },
            "a11y": {
                "requires_audio": False,
                "requires_vision": False,
                "requires_speech": False,
            },
            "version": 1,
            "source": "generated",
        }

    def _closing_block(self, state: InterviewState) -> dict:
        """The end of the interview.

        Warm, brief, and it does not evaluate. The feedback comes from the
        rubric, after, and strengths come first when it does.
        """
        return {
            "id": f"interview.{state.track}.closing",
            "kind": "interview_question",
            "canonical_text": (
                "That is the end of the interview. Thank you for your time — "
                "your feedback is on the next screen."
            ),
            "intent": "close",
            "difficulty": 1,
            "scenario_tags": ["interview", state.track],
            "representations": {
                "caption": "That is the end of the interview. Thank you for your time.",
                "easy_read": "The interview is finished.\nThank you.\nYour feedback is next.",
            },
            "interaction": {
                "accepted_input_modes": ["speech", "text", "aac", "sign", "switch"],
                "target_response": {"type": "acknowledge"},
                "hints": [],
                "choices": [],
            },
            "a11y": {
                "requires_audio": False,
                "requires_vision": False,
                "requires_speech": False,
            },
            "version": 1,
            "source": "authored",
        }


def _track_description(track: str) -> str:
    return {
        "hr": "HR and behavioural questions about experience and ways of working",
        "role": "role-specific questions about the job itself",
        # Harder because it removes visual context, not because it is faster.
        "telephonic": (
            "a telephone interview — no visual cues, so be explicit about who you "
            "are and what you are asking"
        ),
    }.get(track, "HR and behavioural questions")


def _persona_description(persona: str) -> str:
    return {
        "supportive": "warm and encouraging, without being effusive",
        "neutral": "professional and matter-of-fact",
        "brisk": "busy and direct, with short questions — never rude, never rushing them",
    }.get(persona, "warm and encouraging")


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

"""Deriving an FSRS grade from what the learner actually did.

Every spaced-repetition app in existence asks the learner to self-rate: "how
well did you know that?" with an Again/Hard/Good/Easy button. We cannot do that,
for two independent reasons:

  1. Many of our learners cannot reliably self-assess. Asking a learner with an
     intellectual disability to introspect on their own recall quality produces
     noise, and FSRS trained on noise schedules badly.

  2. A self-rating button asks the learner to judge themselves, several times a
     minute, forever. That is a bad experience for anyone, and a corrosive one
     for someone who has spent their life being assessed.

So we derive the grade from observable behaviour instead: was the answer right,
how many attempts did it take, did they use a hint.

WHAT WE DELIBERATELY DO NOT USE
-------------------------------
**Response time.** Not as a tiebreak, not as a bonus, not at all.

This is Ethics rule E6 (no time-pressure mechanics) and rule E2 (response_latency
is on the rubric exclusion list). A learner with dysarthria, a stammer, cerebral
palsy or an intellectual disability takes longer to respond *because of the
disability*, not because they know the material less well. Feeding latency into
the scheduler would make the app quietly re-teach material they already know,
purely for being disabled — and it would look like a neutral algorithm doing it.

`derive_grade` does not take a duration parameter. That is the enforcement:
timing cannot influence scheduling because the function cannot see it.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.learning.fsrs import Grade

#: Above this self-reported confidence, a clean first-attempt answer is Easy.
#: Self-report is optional and only ever *promotes* a grade — it can never
#: demote one, so a learner who under-rates themselves is not punished for it.
CONFIDENT = 4


@dataclass(frozen=True)
class Attempt:
    """What actually happened on one review. No timing field, by design."""

    correct: bool
    #: 1 = right first time. Counts submissions, not keystrokes.
    attempts: int = 1
    #: Hints shown before the learner answered.
    hints_used: int = 0
    #: Optional learner self-report, 1-5. Only ever promotes a grade.
    confidence: int | None = None
    #: True when the answer needed confirming because transcription was
    #: uncertain. Never counted against the learner — see below.
    low_confidence_input: bool = False


def derive_grade(attempt: Attempt) -> Grade:
    """Map an attempt onto an FSRS grade.

    Ordering of the checks matters; each is justified.
    """
    # A transcription we could not trust says nothing about whether the learner
    # knew the phrase. Treating it as a failure would mean an ASR weakness
    # showed up as the learner's weakness — precisely the harm this product
    # exists to correct. Neutral grade, no lapse recorded.
    if attempt.low_confidence_input:
        return Grade.GOOD if attempt.correct else Grade.HARD

    if not attempt.correct:
        return Grade.AGAIN

    # Correct, but it took more than one go or needed help. Genuine partial
    # recall — exactly what HARD is for.
    if attempt.attempts > 1 or attempt.hints_used > 0:
        return Grade.HARD

    if attempt.confidence is not None and attempt.confidence >= CONFIDENT:
        return Grade.EASY

    return Grade.GOOD


def is_lapse(attempt: Attempt) -> bool:
    """Did this attempt break a learning streak?

    Kept separate from the grade because a low-confidence transcription must
    never count as a lapse, even though it produces a non-EASY grade.
    """
    return not attempt.low_confidence_input and not attempt.correct

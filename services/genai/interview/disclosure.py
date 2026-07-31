"""The Accommodation & Disclosure Coach (M11.4).

The feature no competitor has, and the one that needs the most care.

A learner rehearsing disclosure is rehearsing something that can cost them a job.
That is not a reason to avoid the feature — the decision is being made whether we
help or not, and being unprepared for it is worse — but it is a reason to build
it differently from everything else in the product.

FOUR RULES THIS MODULE OBEYS
----------------------------
**1. It never advises whether to disclose.** That is the learner's decision, it
depends on facts we do not have, and a tool that nudges either way is
substituting its judgement for theirs on a question about their own life. The
coach lays out considerations and rehearses both paths.

**2. Both outcomes are practised.** A branch where the employer responds well
and a branch where they do not. A learner who has only ever rehearsed the good
outcome is not prepared, and the bad outcome is the one that needs practice.

**3. There is always an exit.** Every screen carries a way out and a route to a
human trainer. This content is emotionally loaded and a learner may discover
mid-way that they do not want to do it today.

**4. The rights primer is informational and says so.** RPwD Act 2016. Clearly
not legal advice, clearly dated, and it points at where to get the real thing.

WHAT THIS IS NOT
----------------
Not a decision aid that produces a recommendation. Not a legal service. Not a
place to record whether a learner is disabled — the coach never asks, and
nothing here writes to a profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BranchOutcome = Literal["supportive", "neutral", "poor"]


@dataclass(frozen=True)
class Consideration:
    """One thing worth thinking about. Never a recommendation.

    Deliberately paired: every consideration in favour has one against, so the
    set cannot be read as a nudge. A learner reading only the pros of disclosure
    is being steered, however true each individual point is.
    """

    prompt: str
    toward_disclosure: str
    toward_privacy: str


CONSIDERATIONS: tuple[Consideration, ...] = (
    Consideration(
        prompt="Do you need an adjustment to do the job well?",
        toward_disclosure=(
            "If you need something changed — written instructions, a quieter space, "
            "different hours — an employer can only arrange it if they know."
        ),
        toward_privacy=(
            "If you do not need anything changed, there is nothing you are required "
            "to say. Many people never mention it at all."
        ),
    ),
    Consideration(
        prompt="When would you want to say it?",
        toward_disclosure=(
            "Saying it early means you find out sooner what kind of employer they are."
        ),
        toward_privacy=(
            "Saying it after an offer means the decision to hire you was made on "
            "your work."
        ),
    ),
    Consideration(
        prompt="How much do you want to explain?",
        toward_disclosure=(
            "You can name what helps you without naming a diagnosis. \"It helps me "
            "if instructions are written down\" is a complete sentence."
        ),
        toward_privacy=(
            "You are never obliged to explain a diagnosis, provide medical details, "
            "or answer questions about your health history."
        ),
    ),
    Consideration(
        prompt="What do you already know about this employer?",
        toward_disclosure=(
            "An employer with a track record of hiring disabled people is a "
            "different conversation from one without."
        ),
        toward_privacy=(
            "If you know nothing about them yet, waiting until you do is a "
            "reasonable choice."
        ),
    ),
)


@dataclass(frozen=True)
class Phrasing:
    """A way of putting it. Several, because there is no single right one."""

    label: str
    text: str
    easy_read: str
    #: What this phrasing gives away, stated plainly so the learner is choosing
    #: with their eyes open rather than picking the one that sounds nicest.
    discloses: str


PHRASINGS: tuple[Phrasing, ...] = (
    Phrasing(
        label="Ask for what helps, name nothing",
        text="It helps me if instructions are written down. Would that be possible?",
        easy_read="Written instructions help me.\nCan you do that?",
        discloses="Nothing about a diagnosis or a disability.",
    ),
    Phrasing(
        label="Name the barrier, not the condition",
        text=(
            "I find it hard to follow long spoken instructions. If I can have them "
            "in writing, I work well."
        ),
        easy_read="Long spoken instructions are hard for me.\nWriting helps me.\nThen I work well.",
        discloses="That something is difficult, without saying what or why.",
    ),
    Phrasing(
        label="Name it directly",
        text=(
            "I have a hearing disability. Captions help me in meetings, and if people "
            "face me when they speak I follow easily."
        ),
        easy_read="I am deaf.\nCaptions help me in meetings.\nPlease face me when you speak.",
        discloses="The disability itself, and what helps.",
    ),
    Phrasing(
        label="Lead with the work",
        text=(
            "I have done this work for two years. One thing that helps me do it well "
            "is having the steps written down."
        ),
        easy_read="I did this work for two years.\nWritten steps help me do it well.",
        discloses="Nothing, until the employer asks.",
    ),
)


@dataclass(frozen=True)
class Branch:
    """One way an employer might respond, and what the learner can do next."""

    outcome: BranchOutcome
    employer_says: str
    easy_read: str
    #: What is actually happening, named. A learner should be able to recognise
    #: an unlawful question when they meet one.
    what_this_is: str
    responses: tuple[str, ...]
    #: Shown when the branch is a poor response. Never shown otherwise —
    #: offering support nobody needs is its own kind of condescension.
    support: str = ""


BRANCHES: tuple[Branch, ...] = (
    Branch(
        outcome="supportive",
        employer_says=(
            "That is easy to sort out. I will make sure the shift instructions are "
            "printed for you. Anything else that would help?"
        ),
        easy_read="That is easy.\nI will print the instructions.\nDo you need anything else?",
        what_this_is="A good response. This is what the law expects and what good employers do.",
        responses=(
            "Thank you. That is all I need for now.",
            "Thank you. Could I also have a few minutes to read them at the start?",
            "Thank you — that will make a real difference.",
        ),
    ),
    Branch(
        outcome="neutral",
        employer_says=(
            "Right. I would have to check with the team about that. Can I come back to you?"
        ),
        easy_read="I need to ask my team.\nCan I tell you later?",
        what_this_is=(
            "A neutral response. Not a refusal — most managers have simply never "
            "been asked before."
        ),
        responses=(
            "Of course. When would be a good time to follow up?",
            "Yes, that is fine. Shall I email you the details?",
            "Thank you. I am happy to explain more if it helps.",
        ),
    ),
    Branch(
        outcome="poor",
        employer_says=(
            "I see. And how much time would you expect to take off for this? "
            "What exactly is the condition?"
        ),
        easy_read="Will you need days off?\nWhat is wrong with you?",
        what_this_is=(
            "This is not a reasonable question. Under the RPwD Act 2016 an employer "
            "may ask what adjustment you need; they may not require your medical "
            "history to consider you for a job. You do not have to answer it."
        ),
        responses=(
            "I would rather not go into medical details. What I need is written instructions.",
            "My attendance record is good. The adjustment I am asking for is a printed sheet.",
            "I am happy to talk about what helps me work. I would prefer to leave it there.",
        ),
        support=(
            "That question would be uncomfortable for anyone. If it happens to you in "
            "a real interview, you are allowed to decline it — and it tells you "
            "something useful about the employer."
        ),
    ),
)


#: RPwD Act 2016, in plain words. Informational, and it says so at both ends.
RIGHTS_PRIMER: tuple[tuple[str, str], ...] = (
    (
        "You can ask for reasonable adjustments",
        "An employer covered by the Rights of Persons with Disabilities Act 2016 must "
        "make reasonable changes so you can do the job — unless doing so would cause "
        "them disproportionate difficulty.",
    ),
    (
        "You cannot be refused a job for being disabled",
        "If you can do the job with reasonable adjustments, being disabled is not a "
        "lawful reason to refuse you.",
    ),
    (
        "You do not have to share medical details",
        "An employer may ask what adjustment you need. They may not require your "
        "diagnosis or medical history in order to consider you.",
    ),
    (
        "Government and larger employers have duties",
        "Government establishments must reserve posts and publish an equal-opportunity "
        "policy. Many private employers publish one too.",
    ),
    (
        "There is somewhere to complain",
        "Every state has a Commissioner for Persons with Disabilities, and there is a "
        "Chief Commissioner nationally. Complaints go to them.",
    ),
)

DISCLAIMER = (
    "This is general information, not legal advice, and it was written in 2026. "
    "For advice about your own situation, talk to your trainer, a disability rights "
    "organisation, or the Commissioner for Persons with Disabilities in your state."
)

#: Shown on every screen of this feature.
EXIT_OFFER = (
    "You can stop this at any time and nothing is saved. "
    "If you would rather talk it through with a person, your trainer can help."
)


@dataclass
class CoachSession:
    """Where a learner is in the coach.

    Nothing here records whether the learner is disabled, what their disability
    is, or what they decided. The coach is a rehearsal space, and a rehearsal
    space that keeps notes is not one.
    """

    step: Literal["considerations", "phrasing", "branch", "rights"] = "considerations"
    chosen_phrasing: str | None = None
    practised_outcomes: list[BranchOutcome] = field(default_factory=list)

    @property
    def has_practised_a_poor_response(self) -> bool:
        """The branch that matters. A learner who has only rehearsed the good
        outcome is not prepared for the one that needs preparing for."""
        return "poor" in self.practised_outcomes


def considerations() -> list[dict]:
    return [
        {
            "prompt": consideration.prompt,
            "toward_disclosure": consideration.toward_disclosure,
            "toward_privacy": consideration.toward_privacy,
        }
        for consideration in CONSIDERATIONS
    ]


def phrasings() -> list[dict]:
    return [
        {
            "label": phrasing.label,
            "text": phrasing.text,
            "easy_read": phrasing.easy_read,
            "discloses": phrasing.discloses,
        }
        for phrasing in PHRASINGS
    ]


def branch(outcome: BranchOutcome) -> dict:
    match = next((b for b in BRANCHES if b.outcome == outcome), None)
    if match is None:
        raise KeyError(f"Unknown outcome '{outcome}'")

    return {
        "outcome": match.outcome,
        "employer_says": match.employer_says,
        "easy_read": match.easy_read,
        "what_this_is": match.what_this_is,
        "responses": list(match.responses),
        "support": match.support,
        "exit_offer": EXIT_OFFER,
    }


def rights_primer() -> dict:
    return {
        "items": [{"title": title, "text": text} for title, text in RIGHTS_PRIMER],
        "disclaimer": DISCLAIMER,
        "exit_offer": EXIT_OFFER,
    }


def to_content_block(text: str, easy_read: str, block_id: str) -> dict:
    """Everything this module shows goes through the Modality Router too.

    Disclosure content is exactly as subject to the accessibility architecture as
    a flashcard is — arguably more so, since a learner who cannot read dense text
    is precisely the learner most likely to be asked an intrusive question and
    least likely to have been prepared for it.
    """
    return {
        "id": block_id,
        "kind": "instruction",
        "canonical_text": text,
        "intent": "disclosure_coaching",
        "difficulty": 3,
        "scenario_tags": ["self-advocacy", "disclosure"],
        "representations": {"caption": text, "easy_read": easy_read},
        "interaction": {
            "accepted_input_modes": ["speech", "text", "aac", "sign", "switch"],
            "target_response": {"type": "open_response"},
            "hints": [],
            "choices": [],
        },
        "a11y": {"requires_audio": False, "requires_vision": False, "requires_speech": False},
        "version": 1,
        "source": "authored",
    }

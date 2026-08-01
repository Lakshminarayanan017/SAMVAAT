"""Gamification (M12).

Motivation design is where accessibility gets betrayed most casually, because
the standard playbook is built on loss aversion — streaks that break, hearts
that run out, leagues you get demoted from. Every one of those punishes an
absence, and for a learner whose absences are caused by fatigue, illness, a
seizure, a hospital appointment or a carer not being available, that is
punishing the disability itself.

So four rules, each with a test:

  1. **XP rewards EFFORT, not correctness.** A learner who attempts a hard
     phrase and gets it wrong earns as much as one who got it right. We are
     paying for showing up and trying, because that is the behaviour that
     produces learning — and because scoring correctness twice (once in FSRS,
     once in XP) would double the penalty for having a hard day.

  2. **Streaks never break punitively.** We count DAYS PRACTISED, which only
     ever goes up. A current run is tracked and celebrated, but its loss is
     never announced, never shown as a number falling, and never framed as
     something at risk.

  3. **No comparison to other learners.** No leaderboard, no percentile, no
     "you are in the top 20%". ADR-0003 applies to motivation as much as to
     scoring: the learner competes with yesterday's self.

  4. **Badges reward courage and growth**, not just accuracy. Practising a
     disclosure conversation is harder and matters more than getting ten
     greetings right, and the reward should say so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

# ── XP ───────────────────────────────────────────────────────────────────────

#: Base award for finishing an attempt at all.
XP_ATTEMPT = 10

#: Extra for a phrase the learner has never seen. New material costs more
#: courage than review, and the reward should reflect that.
XP_NEW_MATERIAL = 5

#: Extra per difficulty level above 1. Attempting a level-5 self-advocacy
#: phrase earns more than a level-1 greeting whether or not it goes well.
XP_PER_DIFFICULTY = 3

#: Extra for coming back to something that was hard last time. Rewarding the
#: return, which is the moment most learners quit.
XP_RETURNING_TO_A_LAPSE = 8


@dataclass(frozen=True)
class Attempt:
    """What happened, from the motivation system's point of view.

    Note what is absent: whether the answer was CORRECT. XP does not know, and
    must not — see rule 1.
    """

    difficulty: int = 1
    is_new: bool = False
    had_lapsed: bool = False
    #: The learner engaged with the coaching rather than skipping past it.
    reviewed_feedback: bool = False


def award_xp(attempt: Attempt) -> int:
    """XP for one completed attempt.

    Deliberately takes no `correct` flag. There is no signature by which
    correctness could influence this number, which is the strongest form the
    rule can take.
    """
    xp = XP_ATTEMPT
    xp += XP_PER_DIFFICULTY * max(0, attempt.difficulty - 1)
    if attempt.is_new:
        xp += XP_NEW_MATERIAL
    if attempt.had_lapsed:
        xp += XP_RETURNING_TO_A_LAPSE
    if attempt.reviewed_feedback:
        xp += 2
    return xp


# ── Practice days ────────────────────────────────────────────────────────────

#: A run survives this many missed days before it restarts. Not a scarce
#: "freeze token" the learner must spend or hoard — that is loss aversion with
#: extra steps. It is simply how the run is defined.
GRACE_DAYS = 2


@dataclass
class PracticeRecord:
    """Days practised. This number only ever goes up."""

    days_practised: int = 0
    current_run: int = 0
    longest_run: int = 0
    last_practised_on: date | None = None
    #: Set when THIS session followed a real absence.
    #:
    #: Recorded at registration rather than derived later, because once today is
    #: stored the gap is zero and the fact is gone. It is also what the
    #: `came_back` badge reads — the same fact, wanted in two places.
    returned_after_break: bool = False

    def register(self, today: date) -> PracticeRecord:
        """Record a day of practice.

        Idempotent within a day: practising twice does not count twice, so
        nobody is nudged into grinding.
        """
        if self.last_practised_on == today:
            return self

        gap = (today - self.last_practised_on).days if self.last_practised_on else 1
        returned = self.last_practised_on is not None and gap > GRACE_DAYS + 1

        # Within the grace window the run continues. Beyond it, it restarts —
        # quietly. Nothing announces the restart, and `days_practised` is
        # untouched, so the learner's real total never falls.
        run = 1 if returned else self.current_run + 1

        return PracticeRecord(
            days_practised=self.days_practised + 1,
            current_run=run,
            longest_run=max(self.longest_run, run),
            last_practised_on=today,
            returned_after_break=returned,
        )

    def summary(self) -> str:
        """What the learner is told.

        Never mentions a broken run, a day missed, or a streak at risk. If they
        have been away, it welcomes them back and shows the total they have
        actually built — which is the true number and the encouraging one.
        """
        if self.days_practised == 0:
            return "Your first practice. Welcome."

        days = f"{self.days_practised} day" + ("" if self.days_practised == 1 else "s")

        if self.returned_after_break:
            return f"Good to see you again. You have practised on {days}."

        if self.current_run >= 3:
            return f"{self.current_run} days in a row, and {days} altogether."

        return f"You have practised on {days}."


# ── Badges ───────────────────────────────────────────────────────────────────


class BadgeFamily(str, Enum):
    """Four families, and only one of them is about being right.

    COURAGE exists because rehearsing a disclosure conversation is harder, and
    matters more, than getting ten greetings right. GROWTH is measured against
    the learner's own past (ADR-0003), never against anyone else.
    """

    CONSISTENCY = "consistency"
    MASTERY = "mastery"
    COURAGE = "courage"
    GROWTH = "growth"


@dataclass(frozen=True)
class Badge:
    id: str
    family: BadgeFamily
    label: str
    #: Said to the learner when it is earned. Specific and factual — vague
    #: praise reads as pity, and disabled learners get enough of that.
    earned_message: str


BADGES: list[Badge] = [
    Badge("first_practice", BadgeFamily.CONSISTENCY, "First practice",
          "You started. That is the hardest part."),
    Badge("seven_days", BadgeFamily.CONSISTENCY, "Seven days",
          "You have practised on seven different days."),
    Badge("thirty_days", BadgeFamily.CONSISTENCY, "Thirty days",
          "Thirty days of practice. That is a habit now."),
    Badge("came_back", BadgeFamily.CONSISTENCY, "Came back",
          "You came back after a break. That takes more than starting did."),

    Badge("ten_phrases", BadgeFamily.MASTERY, "Ten phrases",
          "Ten phrases you can rely on."),
    Badge("fifty_phrases", BadgeFamily.MASTERY, "Fifty phrases",
          "Fifty phrases. That is most of a working day covered."),

    Badge("first_interview", BadgeFamily.COURAGE, "First interview",
          "You sat a whole practice interview."),
    Badge("hard_scenario", BadgeFamily.COURAGE, "Difficult conversation",
          "You practised a hard conversation. Most people avoid those."),
    Badge("disclosure_rehearsed", BadgeFamily.COURAGE, "Asked for what you need",
          "You rehearsed asking for an adjustment. That is the conversation that "
          "changes the most, and the one people put off longest."),
    Badge("tried_again", BadgeFamily.COURAGE, "Tried again",
          "You came back to something that did not go well. That is how it moves."),

    Badge("own_best", BadgeFamily.GROWTH, "Your best yet",
          "Your best result so far — measured against you, nobody else."),
    Badge("steady_progress", BadgeFamily.GROWTH, "Moving forward",
          "Four weeks of steady progress against your own starting point."),
]

BADGES_BY_ID = {badge.id: badge for badge in BADGES}


@dataclass
class LearnerProgress:
    """Everything the badge rules read. No other learner appears here."""

    days_practised: int = 0
    returned_after_break: bool = False
    phrases_mastered: int = 0
    interviews_completed: int = 0
    hard_scenarios_attempted: int = 0
    disclosure_rehearsed: bool = False
    retried_after_a_lapse: bool = False
    personal_best: bool = False
    weeks_of_progress: int = 0
    earned: set[str] = field(default_factory=set)


def newly_earned(progress: LearnerProgress) -> list[Badge]:
    """Badges earned now and not before.

    Every rule reads only this learner's own history. There is no argument by
    which another learner's performance could enter.
    """
    qualifies = {
        "first_practice": progress.days_practised >= 1,
        "seven_days": progress.days_practised >= 7,
        "thirty_days": progress.days_practised >= 30,
        "came_back": progress.returned_after_break,
        "ten_phrases": progress.phrases_mastered >= 10,
        "fifty_phrases": progress.phrases_mastered >= 50,
        "first_interview": progress.interviews_completed >= 1,
        "hard_scenario": progress.hard_scenarios_attempted >= 1,
        "disclosure_rehearsed": progress.disclosure_rehearsed,
        "tried_again": progress.retried_after_a_lapse,
        "own_best": progress.personal_best,
        "steady_progress": progress.weeks_of_progress >= 4,
    }

    return [
        BADGES_BY_ID[badge_id]
        for badge_id, earned in qualifies.items()
        if earned and badge_id not in progress.earned
    ]

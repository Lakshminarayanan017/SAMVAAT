"""What should I do next? (M13)

Rule-based and transparent, not learned. That is a deliberate choice, not a
placeholder for a "real" model later:

* Every recommendation carries a REASON the learner can read — "because the /r/
  sound has been tricky this week". Explainability here is a product feature,
  not a debug tool. It is also what makes a trainer trust the system enough to
  deploy it, and a trainer who cannot see why an item was chosen will override
  everything or nothing.

* A contextual bandit needs telemetry we do not have and would produce
  suggestions nobody can explain to a special educator. It lands in `[V2]`,
  after the pilot, on top of the reason codes this module already emits.

THE MORALE CONSTRAINT
---------------------
`recent_failure_penalty` deliberately makes the recommender AVOID something the
learner just struggled with. That is scheduling-suboptimal — FSRS would like it
sooner — and it is right anyway. Being handed the thing you just failed, twice,
is how people decide an app is against them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class Reason(str, Enum):
    """Why an item was chosen. Shown to the learner, in their own words.

    A recommendation the learner cannot interrogate is a recommendation they
    have to take on trust, and trust is exactly what a disabled learner has
    least reason to extend to an algorithm.
    """

    DUE = "due"
    OVERDUE = "overdue"
    NEW = "new"
    WEAK_SOUND = "weak_sound"
    GOAL = "goal"
    LOW_CONFIDENCE = "low_confidence"
    VARIETY = "variety"
    EASY_WIN = "easy_win"


#: Learner-facing wording. `{detail}` is filled where the reason has a
#: specific: a phoneme, a job context.
REASON_TEXT: dict[Reason, str] = {
    Reason.DUE: "It is time to see this one again.",
    Reason.OVERDUE: "It has been a while since you practised this.",
    Reason.NEW: "Something new to try.",
    Reason.WEAK_SOUND: "The {detail} sound has been tricky this week.",
    Reason.GOAL: "This comes up in {detail}.",
    Reason.LOW_CONFIDENCE: "You said you were not sure about this one.",
    Reason.VARIETY: "A change from what you have been doing.",
    Reason.EASY_WIN: "One you know well, to start with.",
}


def explain(reason: Reason, detail: str = "") -> str:
    return REASON_TEXT[reason].replace("{detail}", detail)


# ── weights ──────────────────────────────────────────────────────────────────
#
# Tuned by hand and written down, because a number nobody can justify is a
# number nobody can change safely.

W_OVERDUE = 3.0        # closest to being forgotten
W_ERROR_SIGNATURE = 4.0  # the specific thing this learner finds hard
W_GOAL = 2.5           # relevant to the job they are actually preparing for
W_LOW_CONFIDENCE = 2.0  # they told us they were unsure
W_NEW = 1.0
W_VARIETY = 0.5
#: Negative on purpose. See the morale constraint above.
W_RECENT_FAILURE = -6.0

#: A failure stops suppressing an item after this long.
FAILURE_COOLDOWN = timedelta(hours=20)


@dataclass
class Candidate:
    block_id: str
    difficulty: int = 3
    #: Phonemes this phrase exercises, from the content bank.
    phonemes: tuple[str, ...] = ()
    scenario_tags: tuple[str, ...] = ()
    due_at: datetime | None = None
    is_new: bool = False
    last_failed_at: datetime | None = None
    last_self_report: int | None = None
    recently_practised_tags: bool = False


@dataclass
class LearnerContext:
    """What we know about this learner, and nothing about anyone else."""

    #: Phonemes with the worst recent GOP. From the speech pipeline (M6/M7).
    weak_phonemes: tuple[str, ...] = ()
    #: From the Communication Ability Profile: "packaging unit operator".
    job_context: str = ""
    goal_tags: tuple[str, ...] = ()
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Recommendation:
    block_id: str
    score: float
    reason: Reason
    #: Rendered text. The client shows this verbatim; it does not re-derive it,
    #: so there is one wording and it is testable.
    explanation: str


def score_candidate(
    candidate: Candidate, context: LearnerContext
) -> tuple[float, Reason, str]:
    """Score one item, and record the single strongest reason for it.

    One reason, not a list. A learner reading five overlapping justifications
    learns nothing; the strongest one is the honest answer to "why this?".
    """
    score = 0.0
    reasons: list[tuple[float, Reason, str]] = []

    # Overdue-ness
    if candidate.due_at is not None:
        overdue_days = (context.now - candidate.due_at).total_seconds() / 86_400
        if overdue_days >= 0:
            contribution = W_OVERDUE * min(overdue_days + 1, 10) / 10
            score += contribution
            reasons.append(
                (
                    contribution,
                    Reason.OVERDUE if overdue_days > 3 else Reason.DUE,
                    "",
                )
            )

    # The specific sounds this learner finds hard. The highest-weighted signal:
    # it is the one thing here that is genuinely personal.
    shared = [p for p in candidate.phonemes if p in context.weak_phonemes]
    if shared:
        contribution = W_ERROR_SIGNATURE * min(len(shared), 3) / 3
        score += contribution
        reasons.append((contribution, Reason.WEAK_SOUND, _spoken(shared[0])))

    # Relevance to the job they are actually preparing for.
    if context.goal_tags and set(candidate.scenario_tags) & set(context.goal_tags):
        score += W_GOAL
        reasons.append((W_GOAL, Reason.GOAL, context.job_context or "your work"))

    # They told us they were unsure.
    if candidate.last_self_report is not None and candidate.last_self_report <= 2:
        score += W_LOW_CONFIDENCE
        reasons.append((W_LOW_CONFIDENCE, Reason.LOW_CONFIDENCE, ""))

    if candidate.is_new:
        score += W_NEW
        reasons.append((W_NEW, Reason.NEW, ""))

    if not candidate.recently_practised_tags:
        score += W_VARIETY
        reasons.append((W_VARIETY, Reason.VARIETY, ""))

    # Morale. Suppressed, not removed — it will come back tomorrow.
    if (
        candidate.last_failed_at is not None
        and context.now - candidate.last_failed_at < FAILURE_COOLDOWN
    ):
        score += W_RECENT_FAILURE

    if not reasons:
        return score, Reason.VARIETY, explain(Reason.VARIETY)

    _, reason, detail = max(reasons, key=lambda item: item[0])
    return score, reason, explain(reason, detail)


def recommend(
    candidates: list[Candidate],
    context: LearnerContext,
    limit: int = 5,
) -> list[Recommendation]:
    """The next few things to do, strongest first.

    Always opens with something the learner is likely to get right. Confidence
    at the start of a session is what decides whether there is a next session —
    the same reason `build_session` reorders for a likely win.
    """
    if not candidates:
        return []

    scored = [
        Recommendation(candidate.block_id, *score_candidate(candidate, context))
        for candidate in candidates
    ]
    scored.sort(key=lambda item: item.score, reverse=True)

    top = scored[:limit]
    return _open_with_a_win(top, candidates)


def _open_with_a_win(
    picks: list[Recommendation], candidates: list[Candidate]
) -> list[Recommendation]:
    difficulty = {candidate.block_id: candidate.difficulty for candidate in candidates}
    failed = {
        candidate.block_id
        for candidate in candidates
        if candidate.last_failed_at is not None
    }

    if not picks or (difficulty.get(picks[0].block_id, 3) <= 2 and picks[0].block_id not in failed):
        return picks

    for index, pick in enumerate(picks):
        if difficulty.get(pick.block_id, 3) <= 2 and pick.block_id not in failed:
            reordered = [pick, *picks[:index], *picks[index + 1 :]]
            # Re-explained, because "one you know well, to start with" is the
            # honest reason it is first — not whatever put it in the list.
            reordered[0] = Recommendation(
                pick.block_id, pick.score, Reason.EASY_WIN, explain(Reason.EASY_WIN)
            )
            return reordered

    return picks


#: ARPAbet is unreadable to a learner. "the /r/ sound" is not.
_SPOKEN: dict[str, str] = {
    "R": "/r/", "L": "/l/", "S": "/s/", "Z": "/z/", "TH": "/th/", "DH": "/th/",
    "SH": "/sh/", "CH": "/ch/", "JH": "/j/", "V": "/v/", "F": "/f/", "W": "/w/",
    "Y": "/y/", "NG": "/ng/", "P": "/p/", "B": "/b/", "T": "/t/", "D": "/d/",
    "K": "/k/", "G": "/g/", "M": "/m/", "N": "/n/", "HH": "/h/",
}


def _spoken(phoneme: str) -> str:
    return _SPOKEN.get(phoneme.upper(), f"/{phoneme.lower()}/")

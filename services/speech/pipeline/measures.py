"""Turning pipeline output into the five raw measurements the PPI consumes.

Kept separate from `ppi.py` on purpose. The index itself is pure statistics over
numbers and knows nothing about phonemes, transcripts or ONNX sessions, which is
what lets its fairness properties be tested exhaustively in milliseconds. This
module is the only place the two worlds meet.

Every measure below is bounded to 0-100 and oriented so that higher is better
*for that learner*. None of them is shown to a learner in this form — they are
inputs to the baseline comparison, and the baseline comparison is the output.

A NOTE ON INTELLIGIBILITY
-------------------------
Intelligibility is measured as agreement between what the recogniser heard and
what the learner was asked to say. That means a recogniser failure and a learner
difficulty produce the same number, which would be indefensible as an absolute
score — and is exactly why it is never used as one. Against the learner's own
baseline it measures change, and the recogniser's constant weakness cancels.
Closing the remaining gap is M8's entire job, and `wer_before`/`wer_after` on the
speaker profile is how we prove it moved.
"""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.gop import gop_to_percent
from pipeline.ppi import CoachingCue, Dimension
from pipeline.prosody import ProsodyFeatures
from pipeline.types import PronunciationScore, Transcript

#: Self-report runs 1-5 on the client. Mapped linearly onto the same 0-100 range
#: as everything else so the composite is not dominated by unit choice.
CONFIDENCE_MIN = 1
CONFIDENCE_MAX = 5

#: Below this many speaking runs there is no rhythm to measure — one continuous
#: utterance has no variation to be steady or unsteady about.
MIN_RUNS_FOR_RHYTHM = 2


@dataclass(frozen=True)
class MeasurementInput:
    """Everything one attempt can offer. Every field is optional.

    Optional because the pipeline degrades: a deployment with no aligner has no
    pronunciation measure, a learner who skipped the self-report has no
    confidence measure, and both must produce a smaller result rather than a
    wrong one.
    """

    target_text: str
    transcript: Transcript | None = None
    pronunciation: PronunciationScore | None = None
    prosody: ProsodyFeatures | None = None
    #: (type, start_seconds, end_seconds) per detected event, from the M7
    #: classifier. Events, not counts — this module never receives a "how bad".
    disfluency_spans: tuple[tuple[str, float, float], ...] = ()
    self_report_confidence: int | None = None


def raw_dimensions(measurement: MeasurementInput) -> dict[Dimension, float]:
    """The 0-100 measurements available for this attempt.

    A dimension that could not be measured is absent from the mapping rather
    than present with a default. `ppi.compute` renormalises around what is
    there, so an absent measure costs the learner nothing.
    """
    raw: dict[Dimension, float] = {}

    if measurement.transcript is not None:
        raw[Dimension.INTELLIGIBILITY] = intelligibility(
            measurement.transcript.text, measurement.target_text
        )

    # Unreliable alignment means the frame boundaries are noise, and GOP over
    # noisy boundaries is a confident number about nothing. Omitted, not zeroed.
    if measurement.pronunciation is not None and measurement.pronunciation.reliable:
        raw[Dimension.PRONUNCIATION] = gop_to_percent(measurement.pronunciation.phrase_gop)

    if measurement.prosody is not None:
        steadiness = rhythm_steadiness(measurement.prosody)
        if steadiness is not None:
            raw[Dimension.PACE] = steadiness

        if measurement.disfluency_spans:
            raw[Dimension.FLUENCY] = smoothness(
                measurement.disfluency_spans, measurement.prosody.duration_seconds
            )

    if measurement.self_report_confidence is not None:
        raw[Dimension.CONFIDENCE] = confidence(measurement.self_report_confidence)

    return raw


# ── Individual measures ──────────────────────────────────────────────────────


def intelligibility(heard: str, intended: str) -> float:
    """How much of the intended message survived, 0-100.

    Word-level rather than character-level: a learner who says "finished" where
    the target was "completed" has communicated successfully, and a character
    metric would score that closer than "I've finished" versus "I finished",
    which is the opposite of the truth about whether the message got through.
    """
    intended_words = _words(intended)
    heard_words = _words(heard)

    if not intended_words:
        return 100.0
    if not heard_words:
        return 0.0

    distance = _word_edit_distance(heard_words, intended_words)
    error_rate = min(1.0, distance / len(intended_words))
    return 100.0 * (1.0 - error_rate)


def rhythm_steadiness(prosody: ProsodyFeatures) -> float | None:
    """How evenly the speech came out, 0-100. NOT how fast (ADR-0006).

    Computed from the coefficient of variation of the speaking runs: chunks of
    similar length mean an even delivery a listener can follow, wildly uneven
    chunks mean the listener has to work. Absolute speed does not enter, so
    nothing here rewards hurrying and nothing penalises a learner whose speaking
    rate is a fixed characteristic of their disability.

    Returns None when the utterance is a single unbroken run: there is no rhythm
    to measure, and reporting a perfect score for "did not pause" would reward
    the thing several of our learners physically cannot do.
    """
    runs = prosody.speaking_runs_seconds

    if len(runs) < MIN_RUNS_FOR_RHYTHM:
        return None

    mean = sum(runs) / len(runs)
    if mean <= 0:
        return None

    variance = sum((run - mean) ** 2 for run in runs) / len(runs)
    coefficient = (variance**0.5) / mean

    # 1/(1+cv) maps a perfectly even delivery to 1 and degrades smoothly, with
    # no cliff a learner could fall off between two similar attempts.
    return 100.0 / (1.0 + coefficient)


def smoothness(
    spans: tuple[tuple[str, float, float], ...],
    duration_seconds: float,
) -> float:
    """Proportion of the utterance not inside a detected event, 0-100.

    READ THIS BEFORE CHANGING IT. This is not a fluency grade and it is not a
    count of mistakes. It is one input to a baseline comparison, and the learner
    it matters most for — P5, who stammers — has a baseline that already
    contains his disfluency. His index therefore moves when his own speech
    changes and sits at 50 when it does not, which is the correct behaviour and
    the entire point of ADR-0003.

    The invariance test in `tests/test_ppi.py` is what holds this true.
    """
    if duration_seconds <= 0:
        return 100.0

    # Merge overlapping spans first. The detector scans with 50% overlap, so the
    # same event is routinely reported by two windows, and summing the raw spans
    # would double-count it into a far worse number than the speech deserves.
    merged = _merge_spans([(start, end) for _, start, end in spans])
    covered = sum(end - start for start, end in merged)

    return 100.0 * max(0.0, 1.0 - min(1.0, covered / duration_seconds))


def confidence(self_report: int) -> float:
    """Learner self-report, 1-5, mapped to 0-100.

    Self-report rather than anything acoustic. Inferring confidence from voice
    quality or affect would be scoring a manifestation of disability, which is
    on the Ethics E2 exclusion list — and would also be wrong, since flat affect
    and confident feeling coexist perfectly well.
    """
    clamped = max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, self_report))
    return (clamped - CONFIDENCE_MIN) / (CONFIDENCE_MAX - CONFIDENCE_MIN) * 100.0


# ── Cues ─────────────────────────────────────────────────────────────────────


def attach_cues(
    disfluency_cues: tuple[CoachingCue, ...],
    pronunciation: PronunciationScore | None,
    limit: int = 2,
) -> tuple[CoachingCue, ...]:
    """Assemble the coaching cues shown alongside the index.

    Capped at two. The Ethics Charter sets a maximum of two improvement points
    per session because more is not more helpful — it is demoralising, and for a
    learner with an intellectual disability it is unusable. The cap is applied
    here, once, rather than trusted to every caller.

    Disfluency cues come first because they arrive already phrased as strategies
    from the speech-language-pathologist library; a phoneme suggestion is added
    only if there is room.
    """
    cues = list(disfluency_cues[:limit])

    if len(cues) < limit and pronunciation is not None and pronunciation.reliable:
        for symbol in pronunciation.problem_phones:
            if len(cues) >= limit:
                break
            cues.append(
                CoachingCue(
                    dimension=Dimension.PRONUNCIATION,
                    strategy="target sound",
                    message=f"Next time, try giving the {symbol} sound a little more room.",
                )
            )

    return tuple(cues)


# ── Internals ────────────────────────────────────────────────────────────────


def _words(text: str) -> list[str]:
    """Normalise the way the contracts package does, so the client and the
    speech service never disagree about whether an answer matched."""
    cleaned = "".join(
        character if character.isalnum() or character in " '" else " "
        for character in text.lower()
    )
    return cleaned.split()


def _word_edit_distance(heard: list[str], intended: list[str]) -> int:
    """Levenshtein distance over word tokens.

    Two rolling rows rather than a full matrix: utterances are short, but this
    runs on every attempt on a free-tier CPU host and the constant factor is
    free to remove.
    """
    previous = list(range(len(intended) + 1))

    for i, heard_word in enumerate(heard, start=1):
        current = [i]
        for j, intended_word in enumerate(intended, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (heard_word != intended_word),  # substitution
                )
            )
        previous = current

    return previous[-1]


def _merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not spans:
        return []

    ordered = sorted(spans)
    merged = [ordered[0]]

    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged

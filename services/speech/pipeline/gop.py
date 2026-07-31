"""Goodness of Pronunciation.

Pure maths over acoustic-model posteriors. No torch, no model loading — so this,
the piece that actually decides a pronunciation score, is directly testable.

THE DEFINITION
--------------
For an expected phone `p` occupying frames `O_p`:

    GOP(p) = log P(p | O_p) - max over q in Q of log P(q | O_p)

That is: how confident the model is that the learner produced the phone we
expected, relative to the phone it thought was most likely. A value of 0 means
the expected phone was also the model's best guess. Increasingly negative means
the model heard something else.

Frame log-probabilities are averaged over the phone's duration before comparison
(length normalisation), otherwise long phones accumulate more negative evidence
purely for being long and vowels would always score worse than stops.

WHY THIS NUMBER NEVER REACHES A LEARNER
---------------------------------------
The acoustic model was trained overwhelmingly on typical speech. A learner with
dysarthria produces phones that the model genuinely finds unlikely — so their
GOP is low, permanently, no matter how much they improve. Showing it would tell
them daily that they are failing at being non-disabled, which is precisely the
harm this product exists to prevent.

GOP is an input to the baseline-relative Personal Progress Index (M7) and to the
choice of which phoneme to coach next. Nothing else. Ethics E1, ADR-0003.
"""

from __future__ import annotations

import math

import numpy as np

from pipeline.types import AlignedPhone, Alignment, PhoneScore, PronunciationScore

#: Below this, alignment is too poor for the frame boundaries to mean anything
#: and any GOP computed from them would be noise wearing a number's clothes.
MIN_ALIGNMENT_SCORE = 0.3

#: At most this many coaching targets. More than three improvement points is
#: demoralising and unusable — the same rule the interview rubric follows.
MAX_PROBLEM_PHONES = 3

#: A phone must be at least this bad to be worth coaching. Without a floor,
#: every learner gets three "problems" even when they said everything well.
PROBLEM_GOP_THRESHOLD = -1.0

#: Phones shorter than this are usually alignment artefacts rather than real
#: articulations, and scoring them produces noise.
MIN_PHONE_DURATION_S = 0.02


def frames_for(
    phone: AlignedPhone,
    frame_shift_seconds: float,
    total_frames: int,
) -> tuple[int, int]:
    """Frame indices covering a phone, clamped to the posterior matrix."""
    start = int(round(phone.start_seconds / frame_shift_seconds))
    end = int(round(phone.end_seconds / frame_shift_seconds))

    start = max(0, min(start, total_frames - 1))
    end = max(start + 1, min(end, total_frames))
    return start, end


def phone_gop(
    log_posteriors: np.ndarray,
    start_frame: int,
    end_frame: int,
    expected_index: int,
) -> float:
    """GOP for one phone.

    Args:
        log_posteriors: (frames, phones) log-probabilities from the acoustic model.
        start_frame, end_frame: half-open frame range for this phone.
        expected_index: column of the phone we expected.

    Returns:
        <= 0. Zero means the expected phone was the model's own best guess.
    """
    window = log_posteriors[start_frame:end_frame]
    if window.size == 0:
        return 0.0

    # Length-normalise before comparing, so a long vowel is not penalised for
    # simply accumulating more frames than a short stop.
    expected = float(np.mean(window[:, expected_index]))
    best = float(np.mean(np.max(window, axis=1)))

    # Numerically this is <= 0 by construction; clamp so floating-point noise
    # cannot produce a faintly positive score that looks like a bug downstream.
    return min(0.0, expected - best)


def score_alignment(
    log_posteriors: np.ndarray,
    alignment: Alignment,
    phone_to_index: dict[str, int],
    frame_shift_seconds: float = 0.02,
) -> PronunciationScore:
    """GOP for every aligned phone, plus a phrase-level summary."""
    total_frames = log_posteriors.shape[0]
    reliable = alignment.score >= MIN_ALIGNMENT_SCORE

    scores: list[PhoneScore] = []

    for aligned in alignment.phones:
        index = phone_to_index.get(aligned.phone.symbol)
        if index is None:
            # A phone the acoustic model has no output unit for. Skipped rather
            # than scored as zero, which would read as a perfect pronunciation.
            continue

        if aligned.duration_seconds < MIN_PHONE_DURATION_S:
            continue

        start, end = frames_for(aligned, frame_shift_seconds, total_frames)

        scores.append(
            PhoneScore(
                symbol=aligned.phone.symbol,
                gop=phone_gop(log_posteriors, start, end, index),
                duration_seconds=aligned.duration_seconds,
                word_index=aligned.phone.word_index,
            )
        )

    return PronunciationScore(
        phones=scores,
        phrase_gop=aggregate_gop(scores),
        problem_phones=worst_phones(scores),
        reliable=reliable,
    )


def aggregate_gop(scores: list[PhoneScore]) -> float:
    """Duration-weighted mean GOP across a phrase.

    Weighted by duration rather than a flat mean: a phrase is mostly vowels by
    time, and an unweighted mean lets a single mis-hit consonant dominate a
    sentence the learner otherwise said well.
    """
    if not scores:
        return 0.0

    total_duration = sum(score.duration_seconds for score in scores)
    if total_duration <= 0:
        return float(np.mean([score.gop for score in scores]))

    return sum(score.gop * score.duration_seconds for score in scores) / total_duration


def worst_phones(scores: list[PhoneScore], limit: int = MAX_PROBLEM_PHONES) -> list[str]:
    """The phonemes worth coaching next.

    Returns distinct symbols, worst first, and only those below the threshold.
    Without the threshold every learner receives three "problems" even after a
    flawless attempt, which teaches them the number is meaningless.
    """
    candidates = [score for score in scores if score.gop < PROBLEM_GOP_THRESHOLD]
    candidates.sort(key=lambda score: score.gop)

    seen: list[str] = []
    for score in candidates:
        if score.symbol not in seen:
            seen.append(score.symbol)
        if len(seen) >= limit:
            break
    return seen


def to_log_posteriors(logits: np.ndarray) -> np.ndarray:
    """Log-softmax over the phone axis, computed stably.

    Subtracting the row max before exponentiating keeps `exp` inside range; the
    naive form overflows on confident frames and silently yields NaN, which
    would propagate into every score downstream.
    """
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    return shifted - np.log(np.sum(np.exp(shifted), axis=-1, keepdims=True))


def gop_to_percent(gop: float, scale: float = 4.0) -> float:
    """Map GOP onto 0-100 for INTERNAL use only.

    Exposed because the Personal Progress Index needs a bounded input, not
    because this is ever displayed. See the module docstring: raw pronunciation
    numbers are never shown to a learner.
    """
    return 100.0 * math.exp(gop / scale)

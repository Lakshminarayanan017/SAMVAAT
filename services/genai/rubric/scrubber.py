"""Transcript scrubbing — the strongest of the four exclusion layers.

    You cannot penalise what you never received.

The rubric scorer is handed a normalised transcript with disfluencies removed,
pauses collapsed and every timing field stripped. It is not *instructed* to
ignore speech rate, articulation and hesitation; it is structurally incapable of
observing them.

This is layer 1 of the four in Ethics E2. The other three — the response schema
with no field for an excluded trait, the invariance test in CI, and the audit
record — all assume this one ran. It runs first, and nothing reaches the scorer
without passing through it.

WHY THIS IS NOT COSMETIC
------------------------
An unscrubbed transcript of a learner who stammers looks like this:

    "I- I- I w-w-worked at, um, at the... the packaging unit for, uh, two years"

and one from a learner who does not looks like this:

    "I worked at the packaging unit for two years"

Identical content. A language model asked to rate "clarity" will rate the first
lower, every time, no matter what the prompt says — because the first *is* less
fluent, and fluency and clarity are entangled in every text corpus the model has
ever seen. Removing the disfluency is the only intervention that reliably works.

The scrubbed transcript is what the rubric scores. The learner's actual speech
is analysed separately by M7, presented separately, and labelled explicitly as
optional coaching rather than interview performance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Filled pauses and interjections. Removed wholesale — they carry no content
#: and their presence is the single largest confound in text-based scoring.
FILLERS = (
    r"\b(um|uh|erm|er|ah|eh|hmm|mm|mhm)\b",
    r"\b(like|you know|i mean|sort of|kind of)\b(?=[,\s])",
    r"\b(basically|actually|literally)\b",
)

#: Sound and syllable repetition: "I- I- I", "w-w-worked", "th-th-the".
SOUND_REPETITION = re.compile(r"\b(\w{1,3})-(?:\1-)*(?=\w)", re.IGNORECASE)
#: Trailing hyphenated fragments left by a block: "I- I worked".
FRAGMENT = re.compile(r"\b\w{1,3}-\s+")

#: Whole-word repetition: "the the packaging", "I I worked".
#:
#: The separator class includes punctuation, not just whitespace. A learner who
#: blocks after finishing a sentence and restarts the word produces
#: "reliable. Reliable." in the transcript, and a whitespace-only rule leaves it
#: standing — which the invariance gate caught, because the scrubbed forms then
#: differ and the scorer sees two different texts.
#:
#: The trade: this also collapses a legitimate repeat like "had had" or "that
#: that". That is acceptable here and nowhere else. It applies identically to
#: both the clean and the degraded transcript, so it cannot break invariance,
#: and the alternative — leaving a real disfluency in — costs a learner marks
#: for stammering.
WORD_REPETITION = re.compile(r"\b(\w+)(?:[\s.,;:]+\1\b)+", re.IGNORECASE)

#: Pause and hesitation markers, including the ellipses a transcriber inserts
#: for a long silence. Collapsed to a single space: a pause is timing, and
#: timing is on the exclusion list.
PAUSE_MARKERS = re.compile(r"(\.{2,}|—{1,}|\[pause\]|\[silence\]|\[long pause\])", re.IGNORECASE)

#: Transcriber annotations of the kind ASR and human transcription both produce.
ANNOTATIONS = re.compile(r"\[(?:inaudible|unclear|laughs?|sighs?|coughs?|stutters?|blocks?)\]",
                         re.IGNORECASE)

#: Self-corrections. Kept, deliberately — "I worked at, sorry, I managed the
#: packaging unit" is a *content* revision and the final claim is what should be
#: scored. Removing the repair would change the meaning.


@dataclass(frozen=True)
class ScrubResult:
    """The scrubbed text, plus what was removed.

    The removals are recorded but never returned to the scorer. They exist so an
    audit can show the scrubber ran and what it did, and so the invariance test
    can assert the scrubber is the reason the scores match rather than luck.
    """

    text: str
    original_length: int
    removed_fillers: int
    removed_repetitions: int
    removed_pause_markers: int

    @property
    def changed(self) -> bool:
        return bool(self.removed_fillers or self.removed_repetitions or self.removed_pause_markers)

    def audit(self) -> dict:
        return {
            "scrubbed": True,
            "original_length": self.original_length,
            "removed": {
                "fillers": self.removed_fillers,
                "repetitions": self.removed_repetitions,
                "pause_markers": self.removed_pause_markers,
            },
        }


def scrub(transcript: str) -> ScrubResult:
    """Normalise a transcript for rubric scoring.

    Order matters. Sound repetition is removed before word repetition, because
    "w-w-worked worked" needs the fragments gone before the whole-word rule can
    see the duplication. Fillers go before whitespace collapse, because removing
    "um" from "for, um, two years" leaves a double comma that would otherwise
    survive as visible damage.
    """
    original_length = len(transcript)
    text = transcript

    text, annotations = _count_sub(ANNOTATIONS, " ", text)
    text, pause_markers = _count_sub(PAUSE_MARKERS, " ", text)

    fillers = 0
    for pattern in FILLERS:
        text, removed = _count_sub(re.compile(pattern, re.IGNORECASE), " ", text)
        fillers += removed

    text, sound_repetitions = _count_sub(SOUND_REPETITION, "", text)
    text, fragments = _count_sub(FRAGMENT, " ", text)
    text, word_repetitions = _count_sub(WORD_REPETITION, r"\1", text)

    return ScrubResult(
        text=_tidy(text),
        original_length=original_length,
        removed_fillers=fillers,
        removed_repetitions=sound_repetitions + fragments + word_repetitions,
        removed_pause_markers=pause_markers + annotations,
    )


def _count_sub(pattern: re.Pattern, replacement: str, text: str) -> tuple[str, int]:
    result, count = pattern.subn(replacement, text)
    return result, count


def _tidy(text: str) -> str:
    """Repair the punctuation damage removal leaves behind.

    Without this the scrubbed transcript is littered with ", ," and " ." — and a
    model scoring "clarity" on text that looks mangled will mark it down, which
    would reintroduce through the back door exactly the bias the scrubber exists
    to remove.
    """
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*(?=[,.;:!?])", "", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\.{2,}", ".", text)
    return text.strip(" ,;:-")


def strip_timing(payload: dict) -> dict:
    """Remove every timing field before a transcript reaches the scorer.

    Layer 1's second half. Response latency is on the exclusion list, and a
    scorer handed `{"answer": "...", "duration_seconds": 94}` will use it —
    models are extremely good at noticing a number that correlates with
    something, and terrible at being told not to.
    """
    forbidden = {
        "duration_seconds",
        "duration_ms",
        "latency_ms",
        "response_time",
        "started_at",
        "submitted_at",
        "timestamps",
        "word_timings",
        "pauses",
        "speech_rate_wpm",
        "articulation_rate_wpm",
        "disfluency_events",
        "prosody",
        "gop",
        "audio_ref",
    }

    return {
        key: strip_timing(value) if isinstance(value, dict) else value
        for key, value in payload.items()
        if key not in forbidden
    }

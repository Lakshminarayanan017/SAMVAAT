"""Stage contracts for the speech pipeline.

Every stage is a pure function over the previous stage's output. That is what
lets `eval/harness.py` measure any stage in isolation, and it is what stops the
pipeline becoming a single function nobody can test.

    audio -> preprocess -> asr ---------> Transcript
                        -> g2p ---------> ExpectedPhonemes
                        -> align -------> Alignment
                        -> posteriors --> GOP -> PronunciationScore
                        -> prosody -----> ProsodyFeatures   (M7)
                        -> disfluency --> DisfluencyEvents  (M7)
                                            |
                                            v
                                Personal Progress Index     (M7)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Audio:
    """Preprocessed audio. Always 16 kHz mono float32 in [-1, 1]."""

    # numpy.ndarray, typed loosely so the stage contracts need no numpy import.
    samples: object
    sample_rate: int = 16_000

    @property
    def duration_seconds(self) -> float:
        return len(self.samples) / self.sample_rate  # type: ignore[arg-type]


@dataclass(frozen=True)
class Transcript:
    """What the recogniser heard, in the free pass.

    This answers "what did they actually say?" — intelligibility. It is a
    different question from "how well did they say the intended thing?", which
    is what forced alignment plus GOP answers. Conflating the two is the classic
    bug in this kind of pipeline.
    """

    text: str
    confidence: float
    model: str
    language: str = "en"


@dataclass(frozen=True)
class Phone:
    """One expected phoneme, with its position in the target."""

    symbol: str
    word_index: int
    position_in_word: int


@dataclass(frozen=True)
class AlignedPhone:
    """A phoneme located in time by forced alignment."""

    phone: Phone
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class Alignment:
    phones: list[AlignedPhone]
    aligner: str
    #: Overall alignment confidence. A poor alignment invalidates GOP entirely,
    #: so this gates whether a pronunciation score is produced at all.
    score: float = 1.0


@dataclass(frozen=True)
class PhoneScore:
    """Goodness of Pronunciation for one phoneme.

    NEVER SHOWN TO A LEARNER. Raw GOP is a fairness hazard: it is measured
    against an acoustic model trained overwhelmingly on typical speech, so a
    dysarthric speaker scores badly on it no matter how much they improve.
    It feeds the baseline-relative Personal Progress Index (M7) and nothing else
    (Ethics E1, ADR-0003).
    """

    symbol: str
    gop: float
    duration_seconds: float
    word_index: int


@dataclass(frozen=True)
class PronunciationScore:
    """Phrase-level pronunciation, internal to the pipeline."""

    phones: list[PhoneScore]
    #: Duration-weighted mean GOP across the phrase.
    phrase_gop: float
    #: The phonemes worth coaching, worst first. Capped deliberately.
    problem_phones: list[str] = field(default_factory=list)
    #: False when alignment was too poor to trust the scores.
    reliable: bool = True


@dataclass(frozen=True)
class AnalysisResult:
    """Everything the pipeline produced for one attempt."""

    transcript: Transcript | None = None
    alignment: Alignment | None = None
    pronunciation: PronunciationScore | None = None
    #: Stage name -> why it did not run. Surfaced so the client can degrade
    #: honestly rather than showing a learner an empty result.
    skipped: dict[str, str] = field(default_factory=dict)
    model_versions: dict[str, str] = field(default_factory=dict)

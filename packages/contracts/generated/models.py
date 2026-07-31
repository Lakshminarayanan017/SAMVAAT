"""
GENERATED FILE - DO NOT EDIT.

Source of truth: packages/contracts/schemas/*.schema.json
Regenerate with: npm run contracts:build
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Difficulty = int
"""CEFR-mapped difficulty tier. 1 = A1 survival phrases, 5 = C1 nuanced negotiation."""


class AssetRef(BaseModel):
    """A pointer to a media object in storage. Never an inline blob."""

    model_config = ConfigDict(extra="forbid")

    uri: str = Field(..., min_length=1)
    duration_ms: Optional[int] = Field(None, ge=0)
    mime_type: Optional[str] = Field(None)
    checksum: Optional[str] = Field(None)


class IslClip(BaseModel):
    """A human-signed Indian Sign Language video clip. We use recorded clips, not a generated avatar - a bad avatar is worse than none."""

    model_config = ConfigDict(extra="forbid")

    uri: str = Field(..., min_length=1)
    gloss: str = Field(..., description="ISL gloss notation. ISL grammar is not English word order; the gloss records the actual signed sequence.")
    duration_ms: Optional[int] = Field(None, ge=0)
    signer_id: Optional[str] = Field(None)


class Pictograph(BaseModel):
    """A symbol from a CC-licensed AAC set. Mappings are human-verified; automatic mapping produces embarrassing results."""

    model_config = ConfigDict(extra="forbid")

    set: Literal["arasaac", "mulberry"] = Field(...)
    id: Union[int, str] = Field(...)
    label: str = Field(..., min_length=1)
    uri: Optional[str] = Field(None)


class ContentBlockRepresentations(BaseModel):
    """One representation per channel. Missing entries trigger a documented fallback chain and a build-time CI warning - never a runtime surprise for a learner."""

    model_config = ConfigDict(extra="forbid")

    audio_native: Optional[AssetRef] = Field(None)
    audio_slow: Optional[AssetRef] = Field(None)
    isl_clip: Optional[IslClip] = Field(None)
    pictographs: Optional[list[Pictograph]] = Field(None)
    easy_read: Optional[str] = Field(None, description="Easy-Read paraphrase. Human-written, machine-linted: max 15 words per sentence, one clause per line.")
    caption: Optional[str] = Field(None, description="Caption text for the audio. Verbatim, not a paraphrase - captions that paraphrase are a documented failure for Deaf users.")
    phonemes: Optional[str] = Field(None, description="IPA phoneme sequence. G2P-generated, human spot-checked. Feeds forced alignment and GOP scoring (M6).")


class InputMode(str, Enum):
    """How a learner produces an answer. Every mode normalises to LearnerResponse.canonical_text (ADR-0002)."""

    SPEECH = "speech"
    TEXT = "text"
    AAC = "aac"
    SIGN = "sign"
    SWITCH = "switch"


class ContentBlockInteractionTargetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Optional[Literal["phrase_match", "intent_match", "free_form", "choice"]] = Field(None)
    ref: Optional[str] = Field(None)
    choices: Optional[list[str]] = Field(None)


class ContentBlockInteraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_input_modes: list[InputMode] = Field(..., description="Which input modes may answer this block. A block accepting only 'speech' excludes P2 and P4 and will fail contract validation unless a non-speech sibling exists.", min_length=1)
    target_response: Optional[ContentBlockInteractionTargetResponse] = Field(None)
    hints: Optional[list[str]] = Field([])
    distractors: Optional[list[str]] = Field([], description="Plausible wrong options for recognition exercises.")
    common_errors: Optional[list[str]] = Field([], description="Known learner errors, used to pre-write targeted coaching rather than generating it.")


class ContentBlockA11y(BaseModel):
    """Asserted in CI. No ContentBlock may require a channel that a supported profile lacks unless an equivalent representation exists. This is the automated guarantee behind 'accessibility as architecture'."""

    model_config = ConfigDict(extra="forbid")

    requires_audio: bool = Field(...)
    requires_vision: bool = Field(...)
    requires_speech: bool = Field(...)
    notes: Optional[str] = Field(None)


class ContentBlock(BaseModel):
    """A piece of learning content with a canonical meaning and a bundle of representations - but NO chosen rendering. The Modality Router selects representations at runtime from the learner's Communication Ability Profile (ADR-0001). Content authors never decide how something looks, which is why no module can ship inaccessible."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable dotted identifier, e.g. 'phrase.clarify.repeat_request_01'. Never reused, never renamed - progress data references it.", pattern="^[a-z][a-z0-9_]*(\\.[a-z0-9_]+)+$")
    kind: Literal["phrase", "scenario_turn", "social_story_panel", "interview_question", "instruction"] = Field(...)
    canonical_text: str = Field(..., description="The meaning, in plain standard English. This is the reference for scoring, never the thing rendered verbatim to every learner.", min_length=1)
    intent: str = Field(..., description="The communicative function, e.g. 'request_clarification'. Drives scenario matching and the error signature used by the recommender.", min_length=1)
    difficulty: Difficulty = Field(...)
    scenario_tags: Optional[list[str]] = Field([], description="e.g. ['supervisor', 'shopfloor', 'first_week']. Used for RAG filtering in the role-play engine.")
    representations: ContentBlockRepresentations = Field(..., description="One representation per channel. Missing entries trigger a documented fallback chain and a build-time CI warning - never a runtime surprise for a learner.")
    interaction: ContentBlockInteraction = Field(...)
    a11y: ContentBlockA11y = Field(..., description="Asserted in CI. No ContentBlock may require a channel that a supported profile lacks unless an equivalent representation exists. This is the automated guarantee behind 'accessibility as architecture'.")
    version: int = Field(..., ge=1)
    source: Optional[Literal["authored", "generated", "generated_reviewed"]] = Field("authored", description="'generated' content is labelled as AI-generated to the learner until a trainer reviews it (Ethics E5).")


class LearnerResponseRawSignPredictions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(...)
    confidence: float = Field(..., ge=0, le=1)


class LearnerResponseRaw(BaseModel):
    """Mode-specific payload. Only acoustic analytics (GOP, prosody, disfluency) read this, and only when input_mode is 'speech'."""

    model_config = ConfigDict(extra="forbid")

    audio_ref: Optional[str] = Field(None, description="Storage reference. Carries a TTL tag at write time; a scheduled job hard-deletes it within 24h unless research consent was given (Ethics E3).")
    asr_text: Optional[str] = Field(None)
    asr_model: Optional[str] = Field(None)
    symbol_sequence: Optional[list[Union[int, str]]] = Field(None, description="AAC symbol IDs in the order tapped.")
    sign_predictions: Optional[list[LearnerResponseRawSignPredictions]] = Field(None, description="On-device sign classifier output. Only the labels reach the server - video never leaves the device (Ethics E4).")
    typed_text: Optional[str] = Field(None)
    switch_path: Optional[list[str]] = Field(None, description="Scan selections made, for usability analysis of the scanning interface.")


class LearnerResponseTiming(BaseModel):
    """Recorded for analytics ONLY. Latency must never influence a score - that is Ethics E2 (excluded dimension 'response_latency') and E6 (no time pressure)."""

    model_config = ConfigDict(extra="forbid")

    started_at: str = Field(...)
    submitted_at: str = Field(...)
    attempts: Optional[int] = Field(1, ge=1)


class LearnerResponseSelfReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: Optional[int] = Field(None, description="How confident the learner felt. Feeds the recommender; never feeds a score.", ge=1, le=5)
    difficulty_felt: Optional[int] = Field(None, ge=1, le=5)


class LearnerResponse(BaseModel):
    """A learner's answer, normalised so that speaking, typing, signing, tapping symbols and switch-scanning all produce a comparable canonical_text (ADR-0002). One scoring engine, one scheduler, one recommender and one dashboard therefore serve every disability profile."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., min_length=1)
    block_id: str = Field(..., min_length=1)
    input_mode: InputMode = Field(...)
    canonical_text: str = Field(..., description="The normalised answer. Lowercased, punctuation-stripped, comparable across modalities. This is what downstream logic reads.")
    confidence: Optional[float] = Field(None, description="How reliable canonical_text is. Speech and sign are lossy in ways typing is not. Below threshold we ask the learner to confirm - we NEVER score a low-confidence transcription as a wrong answer.", ge=0, le=1)
    raw: Optional[LearnerResponseRaw] = Field(None, description="Mode-specific payload. Only acoustic analytics (GOP, prosody, disfluency) read this, and only when input_mode is 'speech'.")
    timing: LearnerResponseTiming = Field(..., description="Recorded for analytics ONLY. Latency must never influence a score - that is Ethics E2 (excluded dimension 'response_latency') and E6 (no time pressure).")
    self_report: Optional[LearnerResponseSelfReport] = Field(None)
    offline: Optional[bool] = Field(False, description="True if captured without a network. Full analysis is queued and runs on reconnect; the learner is told so explicitly.")
    cap_version: Optional[int] = Field(None, description="Which Communication Ability Profile version this response was collected under. Progress data is only comparable within a CAP version.", ge=1)


class OutputChannel(str, Enum):
    """How content is presented to a learner. The Modality Router composes one primary channel with any number of simultaneous support channels (ADR-0001)."""

    AUDIO = "audio"
    CAPTIONED_TEXT = "captioned_text"
    ISL = "isl"
    PICTOGRAPH = "pictograph"
    EASY_READ = "easy_read"


class TextComplexity(str, Enum):
    """'easy_read' enforces the rules in docs/ACCESSIBILITY.md: 15 words per sentence, one idea per screen, supporting image per idea."""

    STANDARD = "standard"
    EASY_READ = "easy_read"


class SpeechStatus(str, Enum):
    """Drives ASR personalisation (M8) and the PPI dimension weighting (M7). Self-declared during onboarding, never inferred."""

    TYPICAL = "typical"
    ATYPICAL = "atypical"
    NONVERBAL = "nonverbal"
    UNDECLARED = "undeclared"


class CommunicationAbilityProfilePresentation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_rate: Optional[float] = Field(1, description="Playback rate for narrated audio. Below 1.0 uses the recorded slow track where available.", ge=0.5, le=1.5)
    contrast_theme: Optional[Literal["standard", "high_contrast"]] = Field("standard")
    colour_scheme: Optional[Literal["light", "dark", "system"]] = Field("system")
    motion_reduced: Optional[bool] = Field(False)
    target_size_px: Optional[int] = Field(44, description="Minimum interactive target size. 44 is the WCAG 2.2 AA floor; motor-impaired profiles raise it.", ge=44, le=88)
    captions_enabled: Optional[bool] = Field(True)
    one_step_per_screen: Optional[bool] = Field(False, description="Forced true for easy_read profiles. Never more than one idea on screen.")


class CommunicationAbilityProfileInteractionSwitchScanning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: Optional[bool] = Field(False)
    switch_count: Optional[Literal[1, 2]] = Field(2)
    dwell_ms: Optional[int] = Field(1200, ge=300, le=5000)
    scan_mode: Optional[Literal["linear", "row_column"]] = Field("row_column")


class CommunicationAbilityProfileInteraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    switch_scanning: Optional[CommunicationAbilityProfileInteractionSwitchScanning] = Field(None)
    session_length_target_min: Optional[int] = Field(5, description="How long a comfortable session is. The session builder respects this. It is NOT a time limit on any single answer (Ethics E6).", ge=2, le=30)


class CommunicationAbilityProfileScoringWeights(BaseModel):
    """Per-dimension weights for the composite Personal Progress Index (ADR-0003). Visible to the learner and the trainer - never hidden. A profile with a stammer down-weights fluency and up-weights intelligibility."""

    model_config = ConfigDict(extra="forbid")

    intelligibility: Optional[float] = Field(0.3, ge=0, le=1)
    pronunciation: Optional[float] = Field(0.2, ge=0, le=1)
    pace: Optional[float] = Field(0.15, ge=0, le=1)
    fluency: Optional[float] = Field(0.15, ge=0, le=1)
    confidence: Optional[float] = Field(0.2, ge=0, le=1)


class CommunicationAbilityProfileGoals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_context: Optional[str] = Field(None, description="Free text, e.g. 'packaging unit operator'. Grounds social-story and scenario generation in the learner's actual workplace.")
    target_scenarios: Optional[list[str]] = Field([])


class CommunicationAbilityProfileSupport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guardian_managed: Optional[bool] = Field(False)
    guardian_user_id: Optional[str] = Field(None)
    trainer_user_id: Optional[str] = Field(None)
    institution_id: Optional[str] = Field(None)


class CommunicationAbilityProfileEnrolment(BaseModel):
    """Speech enrolment state for personalised ASR (M8). Always skippable and resumable - never a wall between the learner and the product."""

    model_config = ConfigDict(extra="forbid")

    phrases_completed: Optional[int] = Field(0, ge=0)
    phrases_required: Optional[int] = Field(30, ge=0)
    complete: Optional[bool] = Field(False)
    adapter_ref: Optional[str] = Field(None)


class CommunicationAbilityProfile(BaseModel):
    """The single most important object in the system. Describes which channels a learner can actually use. The Modality Router, the scoring weights, the recommender and every dashboard read this. Built during onboarding (M1), versioned - never updated in place, because progress data is only comparable within a version."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    version: int = Field(..., ge=1)
    input_channels: list[InputMode] = Field(..., description="What the learner can use to answer. At least one is required - a profile with none cannot be served.", min_length=1)
    output_channels: list[OutputChannel] = Field(..., description="What the learner can use to receive. Ordered by preference; index 0 is the primary channel and the rest render simultaneously as support.", min_length=1)
    text_complexity: TextComplexity = Field(...)
    speech_status: SpeechStatus = Field(...)
    primary_language: Optional[Literal["en-IN", "ta-IN", "hi-IN"]] = Field("en-IN")
    presentation: Optional[CommunicationAbilityProfilePresentation] = Field(None)
    interaction: Optional[CommunicationAbilityProfileInteraction] = Field(None)
    scoring_weights: Optional[CommunicationAbilityProfileScoringWeights] = Field(None, description="Per-dimension weights for the composite Personal Progress Index (ADR-0003). Visible to the learner and the trainer - never hidden. A profile with a stammer down-weights fluency and up-weights intelligibility.")
    goals: Optional[CommunicationAbilityProfileGoals] = Field(None)
    support: Optional[CommunicationAbilityProfileSupport] = Field(None)
    enrolment: Optional[CommunicationAbilityProfileEnrolment] = Field(None, description="Speech enrolment state for personalised ASR (M8). Always skippable and resumable - never a wall between the learner and the product.")
    created_at: Optional[str] = Field(None)

/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * Source of truth: packages/contracts/schemas/*.schema.json
 * Regenerate with: npm run contracts:build
 */

/* eslint-disable */

// ── Shared definitions (common.schema.json) ─────────────────────────

/**
 * How a learner produces an answer. Every mode normalises to LearnerResponse.canonical_text (ADR-0002).
 */
export type InputMode = 'speech' | 'text' | 'aac' | 'sign' | 'switch';
/**
 * How content is presented to a learner. The Modality Router composes one primary channel with any number of simultaneous support channels (ADR-0001).
 */
export type OutputChannel = 'audio' | 'captioned_text' | 'isl' | 'pictograph' | 'easy_read';
/**
 * 'easy_read' enforces the rules in docs/ACCESSIBILITY.md: 15 words per sentence, one idea per screen, supporting image per idea.
 */
export type TextComplexity = 'standard' | 'easy_read';
/**
 * Drives ASR personalisation (M8) and the PPI dimension weighting (M7). Self-declared during onboarding, never inferred.
 */
export type SpeechStatus = 'typical' | 'atypical' | 'nonverbal' | 'undeclared';
/**
 * CEFR-mapped difficulty tier. 1 = A1 survival phrases, 5 = C1 nuanced negotiation.
 */
export type Difficulty = number;

/**
 * A pointer to a media object in storage. Never an inline blob.
 */
export interface AssetRef {
  uri: string;
  duration_ms?: number;
  mime_type?: string;
  checksum?: string;
}
/**
 * A symbol from a CC-licensed AAC set. Mappings are human-verified; automatic mapping produces embarrassing results.
 */
export interface Pictograph {
  set: 'arasaac' | 'mulberry';
  id: number | string;
  label: string;
  uri?: string;
}
/**
 * A human-signed Indian Sign Language video clip. We use recorded clips, not a generated avatar - a bad avatar is worse than none.
 */
export interface IslClip {
  uri: string;
  /**
   * ISL gloss notation. ISL grammar is not English word order; the gloss records the actual signed sequence.
   */
  gloss: string;
  duration_ms?: number;
  signer_id?: string;
}

export const INPUT_MODE_VALUES: readonly InputMode[] = ['speech', 'text', 'aac', 'sign', 'switch'] as const;
export const OUTPUT_CHANNEL_VALUES: readonly OutputChannel[] = ['audio', 'captioned_text', 'isl', 'pictograph', 'easy_read'] as const;
export const TEXT_COMPLEXITY_VALUES: readonly TextComplexity[] = ['standard', 'easy_read'] as const;
export const SPEECH_STATUS_VALUES: readonly SpeechStatus[] = ['typical', 'atypical', 'nonverbal', 'undeclared'] as const;

// ── Contracts ───────────────────────────────────────────────────────

/**
 * A piece of learning content with a canonical meaning and a bundle of representations - but NO chosen rendering. The Modality Router selects representations at runtime from the learner's Communication Ability Profile (ADR-0001). Content authors never decide how something looks, which is why no module can ship inaccessible.
 */
export interface ContentBlock {
  /**
   * Stable dotted identifier, e.g. 'phrase.clarify.repeat_request_01'. Never reused, never renamed - progress data references it.
   */
  id: string;
  kind: 'phrase' | 'scenario_turn' | 'social_story_panel' | 'interview_question' | 'instruction';
  /**
   * The meaning, in plain standard English. This is the reference for scoring, never the thing rendered verbatim to every learner.
   */
  canonical_text: string;
  /**
   * The communicative function, e.g. 'request_clarification'. Drives scenario matching and the error signature used by the recommender.
   */
  intent: string;
  difficulty: Difficulty;
  /**
   * e.g. ['supervisor', 'shopfloor', 'first_week']. Used for RAG filtering in the role-play engine.
   */
  scenario_tags?: string[];
  /**
   * One representation per channel. Missing entries trigger a documented fallback chain and a build-time CI warning - never a runtime surprise for a learner.
   */
  representations: {
    audio_native?: AssetRef;
    audio_slow?: AssetRef;
    isl_clip?: IslClip;
    pictographs?: Pictograph[];
    /**
     * Easy-Read paraphrase. Human-written, machine-linted: max 15 words per sentence, one clause per line.
     */
    easy_read?: string;
    /**
     * Caption text for the audio. Verbatim, not a paraphrase - captions that paraphrase are a documented failure for Deaf users.
     */
    caption?: string;
    /**
     * IPA phoneme sequence. G2P-generated, human spot-checked. Feeds forced alignment and GOP scoring (M6).
     */
    phonemes?: string;
  };
  interaction: {
    /**
     * Which input modes may answer this block. A block accepting only 'speech' excludes P2 and P4 and will fail contract validation unless a non-speech sibling exists.
     *
     * @minItems 1
     */
    accepted_input_modes: [InputMode, ...InputMode[]];
    target_response?: {
      type?: 'phrase_match' | 'intent_match' | 'free_form' | 'choice';
      ref?: string;
      choices?: string[];
    };
    hints?: string[];
    /**
     * Plausible wrong options for recognition exercises.
     */
    distractors?: string[];
    /**
     * Known learner errors, used to pre-write targeted coaching rather than generating it.
     */
    common_errors?: string[];
  };
  /**
   * Asserted in CI. No ContentBlock may require a channel that a supported profile lacks unless an equivalent representation exists. This is the automated guarantee behind 'accessibility as architecture'.
   */
  a11y: {
    requires_audio: boolean;
    requires_vision: boolean;
    requires_speech: boolean;
    notes?: string;
  };
  version: number;
  /**
   * 'generated' content is labelled as AI-generated to the learner until a trainer reviews it (Ethics E5).
   */
  source?: 'authored' | 'generated' | 'generated_reviewed';
}

/**
 * A learner's answer, normalised so that speaking, typing, signing, tapping symbols and switch-scanning all produce a comparable canonical_text (ADR-0002). One scoring engine, one scheduler, one recommender and one dashboard therefore serve every disability profile.
 */
export interface LearnerResponse {
  session_id: string;
  block_id: string;
  input_mode: InputMode;
  /**
   * The normalised answer. Lowercased, punctuation-stripped, comparable across modalities. This is what downstream logic reads.
   */
  canonical_text: string;
  /**
   * How reliable canonical_text is. Speech and sign are lossy in ways typing is not. Below threshold we ask the learner to confirm - we NEVER score a low-confidence transcription as a wrong answer.
   */
  confidence?: number;
  /**
   * Mode-specific payload. Only acoustic analytics (GOP, prosody, disfluency) read this, and only when input_mode is 'speech'.
   */
  raw?: {
    /**
     * Storage reference. Carries a TTL tag at write time; a scheduled job hard-deletes it within 24h unless research consent was given (Ethics E3).
     */
    audio_ref?: string;
    asr_text?: string;
    asr_model?: string;
    /**
     * AAC symbol IDs in the order tapped.
     */
    symbol_sequence?: (number | string)[];
    /**
     * On-device sign classifier output. Only the labels reach the server - video never leaves the device (Ethics E4).
     */
    sign_predictions?: {
      label: string;
      confidence: number;
    }[];
    typed_text?: string;
    /**
     * Scan selections made, for usability analysis of the scanning interface.
     */
    switch_path?: string[];
  };
  /**
   * Recorded for analytics ONLY. Latency must never influence a score - that is Ethics E2 (excluded dimension 'response_latency') and E6 (no time pressure).
   */
  timing: {
    started_at: string;
    submitted_at: string;
    attempts?: number;
  };
  self_report?: {
    /**
     * How confident the learner felt. Feeds the recommender; never feeds a score.
     */
    confidence?: number;
    difficulty_felt?: number;
  };
  /**
   * True if captured without a network. Full analysis is queued and runs on reconnect; the learner is told so explicitly.
   */
  offline?: boolean;
  /**
   * Which Communication Ability Profile version this response was collected under. Progress data is only comparable within a CAP version.
   */
  cap_version?: number;
}

/**
 * The single most important object in the system. Describes which channels a learner can actually use. The Modality Router, the scoring weights, the recommender and every dashboard read this. Built during onboarding (M1), versioned - never updated in place, because progress data is only comparable within a version.
 */
export interface CommunicationAbilityProfile {
  user_id: string;
  version: number;
  /**
   * What the learner can use to answer. At least one is required - a profile with none cannot be served.
   *
   * @minItems 1
   */
  input_channels: [InputMode, ...InputMode[]];
  /**
   * What the learner can use to receive. Ordered by preference; index 0 is the primary channel and the rest render simultaneously as support.
   *
   * @minItems 1
   */
  output_channels: [OutputChannel, ...OutputChannel[]];
  text_complexity: TextComplexity;
  speech_status: SpeechStatus;
  primary_language?: 'en-IN' | 'ta-IN' | 'hi-IN';
  presentation?: {
    /**
     * Playback rate for narrated audio. Below 1.0 uses the recorded slow track where available.
     */
    audio_rate?: number;
    contrast_theme?: 'standard' | 'high_contrast';
    colour_scheme?: 'light' | 'dark' | 'system';
    motion_reduced?: boolean;
    /**
     * Minimum interactive target size. 44 is the WCAG 2.2 AA floor; motor-impaired profiles raise it.
     */
    target_size_px?: number;
    captions_enabled?: boolean;
    /**
     * Forced true for easy_read profiles. Never more than one idea on screen.
     */
    one_step_per_screen?: boolean;
  };
  interaction?: {
    switch_scanning?: {
      enabled?: boolean;
      switch_count?: 1 | 2;
      dwell_ms?: number;
      scan_mode?: 'linear' | 'row_column';
    };
    /**
     * How long a comfortable session is. The session builder respects this. It is NOT a time limit on any single answer (Ethics E6).
     */
    session_length_target_min?: number;
  };
  /**
   * Per-dimension weights for the composite Personal Progress Index (ADR-0003). Visible to the learner and the trainer - never hidden. A profile with a stammer down-weights fluency and up-weights intelligibility.
   */
  scoring_weights?: {
    intelligibility?: number;
    pronunciation?: number;
    pace?: number;
    fluency?: number;
    confidence?: number;
  };
  goals?: {
    /**
     * Free text, e.g. 'packaging unit operator'. Grounds social-story and scenario generation in the learner's actual workplace.
     */
    job_context?: string;
    target_scenarios?: string[];
  };
  support?: {
    guardian_managed?: boolean;
    guardian_user_id?: string;
    trainer_user_id?: string;
    institution_id?: string;
  };
  /**
   * Speech enrolment state for personalised ASR (M8). Always skippable and resumable - never a wall between the learner and the product.
   */
  enrolment?: {
    phrases_completed?: number;
    phrases_required?: number;
    complete?: boolean;
    adapter_ref?: string;
  };
  created_at?: string;
}

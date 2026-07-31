/**
 * Builds the `LearnerResponse` every input adapter emits.
 *
 * Centralised so no adapter can forget the normalisation, the timing block, or
 * the profile version — and so the confidence threshold is applied identically
 * whatever the input mode.
 */
import {
  CONFIDENCE_CONFIRM_THRESHOLD,
  normaliseText,
  type CommunicationAbilityProfile,
  type ContentBlock,
  type InputMode,
  type LearnerResponse,
} from '@samvaad/contracts';

export interface BuildResponseInput {
  block: ContentBlock;
  profile: CommunicationAbilityProfile;
  sessionId: string;
  inputMode: InputMode;
  /** The learner's answer as text, before normalisation. */
  text: string;
  startedAt: Date;
  attempts?: number;
  /** 0–1. Omit for modes that are not lossy: typing and switch selection. */
  confidence?: number;
  raw?: LearnerResponse['raw'];
  offline?: boolean;
}

export function buildResponse(input: BuildResponseInput): LearnerResponse {
  const {
    block,
    profile,
    sessionId,
    inputMode,
    text,
    startedAt,
    attempts = 1,
    confidence,
    raw,
    offline = false,
  } = input;

  return {
    session_id: sessionId,
    block_id: block.id,
    input_mode: inputMode,
    canonical_text: normaliseText(text),
    ...(confidence === undefined ? {} : { confidence }),
    ...(raw ? { raw } : {}),
    timing: {
      started_at: startedAt.toISOString(),
      submitted_at: new Date().toISOString(),
      attempts,
    },
    offline,
    cap_version: profile.version,
  } as LearnerResponse;
}

/**
 * Should we ask the learner to confirm rather than scoring this?
 *
 * Speech and sign are lossy in ways typing is not. Scoring a bad transcription
 * as a bad answer is exactly how mainstream speech tools fail people with
 * atypical speech, so below the threshold we ask instead of judging.
 */
export function needsConfirmation(response: LearnerResponse): boolean {
  return (
    response.confidence !== undefined &&
    response.confidence !== null &&
    response.confidence < CONFIDENCE_CONFIRM_THRESHOLD
  );
}

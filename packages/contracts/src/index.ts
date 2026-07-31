/**
 * @samvaad/contracts — the data contracts every part of SAMVAAD depends on.
 *
 * JSON Schema in `schemas/` is the single source of truth. TypeScript types are
 * generated into `generated/types.ts`; Pydantic models into `generated/models.py`.
 * CI fails if either drifts from the schemas.
 *
 * Read docs/ADR/0001 and 0002 before changing anything here — these two shapes
 * are why the product is accessible by construction rather than by discipline.
 */

export type {
  ContentBlock,
  LearnerResponse,
  CommunicationAbilityProfile,
} from '../generated/types.js';

export type {
  InputMode,
  OutputChannel,
  TextComplexity,
  SpeechStatus,
  Difficulty,
  AssetRef,
  Pictograph,
  IslClip,
} from '../generated/types.js';

export {
  INPUT_MODE_VALUES,
  OUTPUT_CHANNEL_VALUES,
  TEXT_COMPLEXITY_VALUES,
  SPEECH_STATUS_VALUES,
} from '../generated/types.js';

export * from './guards.js';

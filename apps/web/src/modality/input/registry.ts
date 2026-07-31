/**
 * The input adapter registry.
 *
 * An adapter knows how to collect an answer through ONE input mode and emit a
 * `LearnerResponse` carrying a normalised `canonical_text`. Because every mode
 * produces the same shape, one scoring engine, one scheduler, one recommender
 * and one dashboard serve all five personas (ADR-0002).
 *
 * Same boundary rule as the output side: feature code renders <ModalityInput/>
 * and may not import an adapter directly. ESLint enforces it.
 */
import type { ReactNode } from 'react';
import type {
  CommunicationAbilityProfile,
  ContentBlock,
  InputMode,
  LearnerResponse,
} from '@samvaad/contracts';

export interface InputAdapterProps {
  block: ContentBlock;
  profile: CommunicationAbilityProfile;
  sessionId: string;
  /** Called once the learner submits. Never called on keystroke or partial input. */
  onResponse: (response: LearnerResponse) => void;
  /**
   * Blocks submission while a previous answer is still being processed.
   *
   * Never used to impose a time limit — Ethics E6. There is no path in this
   * codebase that disables an input because the learner took too long.
   */
  disabled?: boolean;
}

export type InputAdapter = (props: InputAdapterProps) => ReactNode;

const registry = new Map<InputMode, InputAdapter>();

export function registerInputAdapter(mode: InputMode, adapter: InputAdapter): void {
  if (registry.has(mode)) {
    throw new Error(
      `An input adapter for '${mode}' is already registered. Two adapters for one mode ` +
        'means the input a learner receives depends on module import order.',
    );
  }
  registry.set(mode, adapter);
}

export function getInputAdapter(mode: InputMode): InputAdapter | undefined {
  return registry.get(mode);
}

export function registeredInputModes(): InputMode[] {
  return [...registry.keys()];
}

/**
 * The input mode to use, given what the block accepts and what the learner can do.
 *
 * Returns `undefined` when there is no overlap — a content authoring bug that
 * the A11Y-3 contract rule is supposed to prevent, but which the UI must still
 * handle rather than rendering a dead screen.
 */
export function resolveInputMode(
  block: ContentBlock,
  profile: CommunicationAbilityProfile,
): InputMode | undefined {
  const accepted = block.interaction.accepted_input_modes;
  // Profile order is preference order: the learner's first listed channel wins.
  return profile.input_channels.find(
    (mode) => accepted.includes(mode) && registry.has(mode),
  );
}

/** Test-only. Never call this from application code. */
export function __resetInputRegistry(): void {
  registry.clear();
}

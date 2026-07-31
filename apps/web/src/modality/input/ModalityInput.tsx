/**
 * The input counterpart to the Modality Router.
 *
 * Feature code renders this and never chooses how the learner answers:
 *
 *     <ModalityInput block={block} sessionId={id} onResponse={handle} />
 *
 * Whichever adapter appears, it emits the same `LearnerResponse` carrying a
 * normalised `canonical_text` — which is why one scoring engine, one scheduler
 * and one set of dashboards serve every persona (ADR-0002).
 */
import type { CommunicationAbilityProfile, ContentBlock, InputMode, LearnerResponse } from '@samvaad/contracts';

import { useProfile } from '@/a11y/ProfileProvider';

import { getInputAdapter, resolveInputMode } from './registry';
import './register';

export interface ModalityInputProps {
  block: ContentBlock;
  sessionId: string;
  onResponse: (response: LearnerResponse) => void;
  disabled?: boolean;
  /**
   * Overrides the learner's profile. Only for the channel-comparison view and
   * tests — production code must let the profile decide.
   */
  forceMode?: InputMode;
}

export function ModalityInput({
  block,
  sessionId,
  onResponse,
  disabled,
  forceMode,
}: ModalityInputProps) {
  const { profile } = useProfile();
  const mode = forceMode ?? resolveInputMode(block, profile);

  if (!mode) return <NoUsableInput block={block} profile={profile} />;

  const Adapter = getInputAdapter(mode);
  if (!Adapter) {
    console.error(`No input adapter registered for mode '${mode}'.`);
    return <NoUsableInput block={block} profile={profile} />;
  }

  return (
    <div data-testid="modality-input" data-input-mode={mode}>
      <Adapter
        block={block}
        profile={profile}
        sessionId={sessionId}
        onResponse={onResponse}
        {...(disabled === undefined ? {} : { disabled })}
      />
    </div>
  );
}

/**
 * Shown when nothing the block accepts overlaps with what the learner can use.
 *
 * The A11Y-3 contract rule exists to make this unreachable, and CI enforces it
 * on all authored content. It is rendered anyway because a content bug must
 * never present a learner with a blank space and no explanation.
 */
function NoUsableInput({
  block,
  profile,
}: {
  block: ContentBlock;
  profile: CommunicationAbilityProfile;
}) {
  console.error(
    `Block '${block.id}' accepts [${block.interaction.accepted_input_modes.join(', ')}] but the ` +
      `learner's profile offers [${profile.input_channels.join(', ')}]. This violates ` +
      'contract rule A11Y-3 and should have been caught in CI.',
  );

  return (
    <div data-testid="modality-input" data-state="no-usable-input" role="alert">
      <p style={{ margin: 0 }}>This activity cannot be answered in a way that works for you.</p>
      <p style={{ margin: 'var(--space-sm, 0.5rem) 0 0', color: 'var(--colour-fg-muted)' }}>
        That is our mistake, not yours. Please skip it — we have been told about the problem.
      </p>
    </div>
  );
}

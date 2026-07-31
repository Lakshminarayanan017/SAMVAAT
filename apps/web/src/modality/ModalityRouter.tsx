/**
 * The Modality Router — the architectural heart of SAMVAAD.
 *
 * Turns a modality-neutral ContentBlock into a rendered experience for one
 * learner's Communication Ability Profile. Feature code renders this and never
 * chooses a channel:
 *
 *     <ModalityRouter block={block} />
 *
 * It composes the learner's PRIMARY channel with every SUPPORTING channel the
 * block can actually satisfy. A learner using Easy-Read typically receives
 * Easy-Read text, a pictograph strip and narrated audio simultaneously — the
 * same block, three renderings, one authored source.
 *
 * See docs/ADR/0001-modality-neutral-content.md.
 */
import { channelsFor, type ContentBlock, type OutputChannel } from '@samvaad/contracts';

import { useProfile } from '@/a11y/ProfileProvider';
import { VISUALLY_HIDDEN } from '@/a11y/Announcer';

import { getRenderer } from './registry';
import './register';

export interface ModalityRouterProps {
  block: ContentBlock;
  /**
   * Overrides the learner's profile. Only for the channel-comparison view and
   * tests — production code must let the profile decide.
   */
  forceChannel?: OutputChannel;
}

export function ModalityRouter({ block, forceChannel }: ModalityRouterProps) {
  const { profile } = useProfile();

  const { primary, support } = forceChannel
    ? { primary: forceChannel, support: [] as OutputChannel[] }
    : channelsFor(block, profile);

  const PrimaryRenderer = getRenderer(primary);

  if (!PrimaryRenderer) {
    // Unreachable in a correctly registered build; the registry is populated at
    // import time. Rendering the canonical text is still better than rendering
    // nothing, and the console error tells us the registry is misconfigured.
    console.error(`No renderer registered for channel '${primary}'.`);
    return <p>{block.canonical_text}</p>;
  }

  return (
    <div data-testid="modality-router" data-primary-channel={primary}>
      {/* Names the rendering for screen-reader users so the mode is discoverable
          rather than implicit. Hidden visually because sighted users can see it. */}
      <span style={VISUALLY_HIDDEN}>{CHANNEL_LABEL[primary]}</span>

      <PrimaryRenderer block={block} profile={profile} />

      {support.length > 0 && (
        <div
          data-testid="support-channels"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-md, 1rem)',
            marginTop: 'var(--space-md, 1rem)',
          }}
        >
          {support.map((channel) => {
            const SupportRenderer = getRenderer(channel);
            if (!SupportRenderer) return null;
            return (
              <div key={channel} data-support-channel={channel}>
                <SupportRenderer block={block} profile={profile} isSupport />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const CHANNEL_LABEL: Record<OutputChannel, string> = {
  audio: 'Spoken audio with transcript',
  captioned_text: 'Text',
  isl: 'Indian Sign Language video',
  pictograph: 'Picture symbols',
  easy_read: 'Easy-Read text',
};

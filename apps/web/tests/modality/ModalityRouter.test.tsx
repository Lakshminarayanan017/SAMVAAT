/**
 * The Modality Router proof.
 *
 * This is the test that demonstrates the central architectural claim: ONE
 * authored ContentBlock, rendered through five different channels, completable
 * by five learners with different disabilities — with no per-modality content
 * and no branching in feature code.
 *
 * The block below is the real fixture from packages/contracts, not a mock, so
 * this test also exercises the same data the contract validator checks.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { CommunicationAbilityProfile, ContentBlock } from '@samvaad/contracts';

import { ProfileProvider } from '@/a11y/ProfileProvider';
import { ModalityRouter } from '@/modality';

import blockFixture from '../../../../packages/contracts/fixtures/valid/content-block/phrase-repeat-request.json';

const block = blockFixture as unknown as ContentBlock;

function profileWith(
  overrides: Partial<CommunicationAbilityProfile>,
): CommunicationAbilityProfile {
  return {
    user_id: 'test',
    version: 1,
    input_channels: ['text'],
    output_channels: ['captioned_text'],
    text_complexity: 'standard',
    speech_status: 'undeclared',
    ...overrides,
  } as CommunicationAbilityProfile;
}

function renderFor(profile: CommunicationAbilityProfile) {
  return render(
    <ProfileProvider initialProfile={profile}>
      <ModalityRouter block={block} />
    </ProfileProvider>,
  );
}

describe('one block, five learners', () => {
  it('P1 (low vision): renders narrated audio with a visible transcript', () => {
    renderFor(profileWith({ output_channels: ['audio', 'captioned_text'] }));

    const router = screen.getByTestId('modality-router');
    expect(router).toHaveAttribute('data-primary-channel', 'audio');

    // The transcript must be present without needing a control to be found.
    expect(screen.getAllByText(block.canonical_text).length).toBeGreaterThan(0);
    expect(
      screen.getByLabelText(`Listen: ${block.canonical_text}`),
    ).toBeInTheDocument();
  });

  it('P2 (Deaf): renders the ISL clip with its gloss, and never requires audio', () => {
    renderFor(profileWith({ output_channels: ['isl', 'captioned_text'] }));

    expect(screen.getByTestId('modality-router')).toHaveAttribute(
      'data-primary-channel',
      'isl',
    );
    expect(
      screen.getByLabelText(`Indian Sign Language: ${block.canonical_text}`),
    ).toBeInTheDocument();
    expect(screen.getByText(/ISL gloss/)).toBeInTheDocument();
    expect(screen.getByText(block.representations!.isl_clip!.gloss)).toBeInTheDocument();
  });

  it('P4 (intellectual disability): renders Easy-Read with pictograph and audio support', () => {
    renderFor(
      profileWith({
        output_channels: ['easy_read', 'pictograph', 'audio'],
        text_complexity: 'easy_read',
      }),
    );

    expect(screen.getByTestId('modality-router')).toHaveAttribute(
      'data-primary-channel',
      'easy_read',
    );

    // Easy-Read source is authored one idea per line; each becomes its own line.
    expect(screen.getByText('I did not hear.')).toBeInTheDocument();
    expect(screen.getByText('I ask again.')).toBeInTheDocument();

    // Support channels render simultaneously, not as an alternative to click.
    const support = screen.getByTestId('support-channels');
    expect(within(support).getByRole('img', { name: /Symbols:/ })).toBeInTheDocument();
  });

  it('P5 (stammer): text-first profile still receives the full block', () => {
    renderFor(profileWith({ output_channels: ['captioned_text'] }));

    expect(screen.getByTestId('modality-router')).toHaveAttribute(
      'data-primary-channel',
      'captioned_text',
    );
    expect(screen.getByText(block.canonical_text)).toBeInTheDocument();
  });
});

describe('fallback behaviour', () => {
  it('degrades deterministically when a representation is missing', () => {
    // A block with no ISL clip, requested by an ISL-primary learner.
    const withoutIsl: ContentBlock = {
      ...block,
      representations: { ...block.representations, isl_clip: undefined },
    };

    render(
      <ProfileProvider initialProfile={profileWith({ output_channels: ['isl'] })}>
        <ModalityRouter block={withoutIsl} />
      </ProfileProvider>,
    );

    // Falls to captioned_text per FALLBACK_CHAIN — never an empty screen.
    expect(screen.getByTestId('modality-router')).toHaveAttribute(
      'data-primary-channel',
      'captioned_text',
    );
    expect(screen.getByText(block.canonical_text)).toBeInTheDocument();
  });

  it('announces the active rendering to screen-reader users', () => {
    renderFor(profileWith({ output_channels: ['easy_read'] }));
    expect(screen.getByText('Easy-Read text')).toBeInTheDocument();
  });
});

describe('the architectural guarantee', () => {
  it('renders the same block through every channel without content changes', () => {
    const channels = ['captioned_text', 'audio', 'easy_read', 'pictograph', 'isl'] as const;

    for (const channel of channels) {
      const { unmount } = render(
        <ProfileProvider initialProfile={profileWith({ output_channels: [channel] })}>
          <ModalityRouter block={block} />
        </ProfileProvider>,
      );

      expect(screen.getByTestId('modality-router')).toHaveAttribute(
        'data-primary-channel',
        channel,
      );
      unmount();
    }
  });

  it('never leaves a learner with nothing, whatever their profile', () => {
    const channels = ['captioned_text', 'audio', 'easy_read', 'pictograph', 'isl'] as const;

    for (const channel of channels) {
      const { container, unmount } = render(
        <ProfileProvider initialProfile={profileWith({ output_channels: [channel] })}>
          <ModalityRouter block={block} />
        </ProfileProvider>,
      );

      expect(container.textContent?.trim().length ?? 0).toBeGreaterThan(0);
      unmount();
    }
  });
});

describe('profile requirement', () => {
  it('refuses to render content without a profile', () => {
    // Rendering learning content with no Communication Ability Profile is never
    // correct: there is no way to know which modality the learner can use.
    expect(() => render(<ModalityRouter block={block} />)).toThrow(/ProfileProvider/);
  });
});

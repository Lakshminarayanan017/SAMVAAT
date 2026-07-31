/**
 * Automated accessibility conformance.
 *
 * Sweeps every output channel and every input mode, because a violation in one
 * rendering says nothing about the others — that is exactly the failure the
 * Modality Router exists to prevent, and it would be embarrassing to reintroduce
 * it inside the router itself.
 */
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type {
  CommunicationAbilityProfile,
  ContentBlock,
  InputMode,
  OutputChannel,
} from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { ModalityInput, ModalityRouter } from '@/modality';
import { CapabilitiesProvider, NO_CAPABILITIES } from '@/services/capabilities';

import blockFixture from '../../../../packages/contracts/fixtures/valid/content-block/phrase-repeat-request.json';
import { blockingViolations, checkA11y, formatViolations } from './axe';

const block = blockFixture as unknown as ContentBlock;

const OUTPUT_CHANNELS: OutputChannel[] = [
  'captioned_text',
  'audio',
  'easy_read',
  'pictograph',
  'isl',
];

const INPUT_MODES: InputMode[] = ['text', 'aac', 'switch', 'speech', 'sign'];

function profileFor(channel: OutputChannel, mode: InputMode): CommunicationAbilityProfile {
  return {
    user_id: 'axe',
    version: 1,
    input_channels: [mode],
    output_channels: [channel],
    text_complexity: channel === 'easy_read' ? 'easy_read' : 'standard',
    speech_status: 'undeclared',
  } as CommunicationAbilityProfile;
}

async function expectNoViolations(container: Element) {
  const results = await checkA11y(container);
  const blocking = blockingViolations(results);

  expect(blocking, formatViolations({ ...results, violations: blocking })).toHaveLength(0);
}

describe.each(OUTPUT_CHANNELS)('output channel: %s', (channel) => {
  it('has no critical or serious violations', async () => {
    const { container } = render(
      <AnnouncerProvider>
        <ProfileProvider initialProfile={profileFor(channel, 'text')}>
          <main>
            <h1>Lesson</h1>
            <ModalityRouter block={block} forceChannel={channel} />
          </main>
        </ProfileProvider>
      </AnnouncerProvider>,
    );

    await expectNoViolations(container);
  });
});

describe.each(INPUT_MODES)('input mode: %s', (mode) => {
  it('has no critical or serious violations', async () => {
    const { container } = render(
      <CapabilitiesProvider initial={NO_CAPABILITIES}>
        <AnnouncerProvider>
          <ProfileProvider initialProfile={profileFor('captioned_text', mode)}>
            <main>
              <h1>Lesson</h1>
              <ModalityInput block={block} sessionId="axe" onResponse={() => {}} />
            </main>
          </ProfileProvider>
        </AnnouncerProvider>
      </CapabilitiesProvider>,
    );

    await expectNoViolations(container);
  });
});

describe('a combined lesson screen', () => {
  it('is clean with a primary channel, support channels and an input together', async () => {
    const profile = {
      user_id: 'axe-combined',
      version: 1,
      input_channels: ['aac'],
      output_channels: ['easy_read', 'pictograph', 'audio'],
      text_complexity: 'easy_read',
      speech_status: 'typical',
    } as CommunicationAbilityProfile;

    const { container } = render(
      <CapabilitiesProvider initial={NO_CAPABILITIES}>
        <AnnouncerProvider>
          <ProfileProvider initialProfile={profile}>
            <main>
              <h1>Asking someone to repeat</h1>
              <ModalityRouter block={block} />
              <ModalityInput block={block} sessionId="axe" onResponse={() => {}} />
            </main>
          </ProfileProvider>
        </AnnouncerProvider>
      </CapabilitiesProvider>,
    );

    await expectNoViolations(container);
  });
});

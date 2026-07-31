/**
 * The input-side proof.
 *
 * The router test showed all five personas can RECEIVE a lesson. This shows all
 * five can ANSWER it — and that every mode produces the same LearnerResponse
 * shape, which is what lets one scoring engine serve all of them (ADR-0002).
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { CommunicationAbilityProfile, ContentBlock, LearnerResponse } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { ModalityInput } from '@/modality';
import { CapabilitiesProvider, NO_CAPABILITIES } from '@/services/capabilities';

import blockFixture from '../../../../packages/contracts/fixtures/valid/content-block/phrase-repeat-request.json';

const block = blockFixture as unknown as ContentBlock;

function profileWith(overrides: Partial<CommunicationAbilityProfile>): CommunicationAbilityProfile {
  return {
    user_id: 'test',
    version: 4,
    input_channels: ['text'],
    output_channels: ['captioned_text'],
    text_complexity: 'standard',
    speech_status: 'undeclared',
    ...overrides,
  } as CommunicationAbilityProfile;
}

function setup(profile: CommunicationAbilityProfile, target: ContentBlock = block) {
  const onResponse = vi.fn<(r: LearnerResponse) => void>();

  const { unmount } = render(
    <CapabilitiesProvider initial={NO_CAPABILITIES}>
      <AnnouncerProvider>
        <ProfileProvider initialProfile={profile}>
          <ModalityInput block={target} sessionId="sess_test" onResponse={onResponse} />
        </ProfileProvider>
      </AnnouncerProvider>
    </CapabilitiesProvider>,
  );

  return { onResponse, unmount, user: userEvent.setup() };
}

describe('every persona can answer', () => {
  it('P5 (stammer) types an answer', async () => {
    const { onResponse, user } = setup(profileWith({ input_channels: ['text'] }));

    await user.type(screen.getByLabelText('Your answer'), 'Could you please repeat that?');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    expect(onResponse).toHaveBeenCalledOnce();
    const response = onResponse.mock.calls[0]![0];
    expect(response.input_mode).toBe('text');
    expect(response.canonical_text).toBe('could you please repeat that');
  });

  it('P4 (AAC user) composes an answer from picture symbols', async () => {
    const { onResponse, user } = setup(profileWith({ input_channels: ['aac'] }));

    await user.click(screen.getByRole('button', { name: /again/ }));
    await user.click(screen.getByRole('button', { name: /please/ }));
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    const response = onResponse.mock.calls[0]![0];
    expect(response.input_mode).toBe('aac');
    expect(response.canonical_text).toBe('again please');
    expect(response.raw?.symbol_sequence).toHaveLength(2);
  });

  it('P3 (switch user) selects an answer from choices', async () => {
    const { onResponse, user } = setup(
      profileWith({
        input_channels: ['switch'],
        interaction: {
          switch_scanning: { enabled: true, switch_count: 2, dwell_ms: 1800, scan_mode: 'linear' },
        },
      } as Partial<CommunicationAbilityProfile>),
    );

    await user.click(screen.getByRole('button', { name: block.canonical_text }));

    const response = onResponse.mock.calls[0]![0];
    expect(response.input_mode).toBe('switch');
    expect(response.canonical_text).toBe('could you please repeat that');
  });

  it('P2 (Deaf, sign-first) is told signing is not ready and pointed at a working path', () => {
    setup(profileWith({ input_channels: ['sign'] }));

    expect(screen.getByText(/Signing to the camera is not ready yet/)).toBeInTheDocument();
    expect(screen.getByText(/Video never leaves your phone/)).toBeInTheDocument();
  });

  it('P1 (speech user) is told plainly when ASR is unavailable, not left on a spinner', () => {
    setup(profileWith({ input_channels: ['speech'] }));

    expect(screen.getByText(/Spoken answers are not available yet/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing here needs speech/)).toBeInTheDocument();
  });
});

describe('the canonical_text guarantee', () => {
  it('produces an identical canonical_text from typing and from symbols', async () => {
    const typed = setup(profileWith({ input_channels: ['text'] }));
    await typed.user.type(screen.getByLabelText('Your answer'), 'Again, please!');
    await typed.user.click(screen.getByRole('button', { name: 'Send answer' }));
    const fromTyping = typed.onResponse.mock.calls[0]![0].canonical_text;

    typed.unmount();

    const tapped = setup(profileWith({ input_channels: ['aac'] }));
    await tapped.user.click(screen.getByRole('button', { name: /again/ }));
    await tapped.user.click(screen.getByRole('button', { name: /please/ }));
    await tapped.user.click(screen.getByRole('button', { name: 'Send answer' }));
    const fromSymbols = tapped.onResponse.mock.calls[0]![0].canonical_text;

    // Punctuation, capitalisation and input mode all differ; the comparable
    // answer does not. This is the whole point of ADR-0002.
    expect(fromTyping).toBe('again please');
    expect(fromSymbols).toBe('again please');
  });

  it('stamps every response with the profile version it was collected under', async () => {
    const { onResponse, user } = setup(profileWith({ input_channels: ['text'], version: 7 }));

    await user.type(screen.getByLabelText('Your answer'), 'yes');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    expect(onResponse.mock.calls[0]![0].cap_version).toBe(7);
  });
});

describe('ethics rule E6 — no time pressure', () => {
  it('never disables an input because time has passed', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { user } = setup(profileWith({ input_channels: ['text'] }));

    await vi.advanceTimersByTimeAsync(10 * 60 * 1000); // ten minutes

    const send = screen.getByRole('button', { name: 'Send answer' });
    await user.type(screen.getByLabelText('Your answer'), 'still here');

    await waitFor(() => expect(send).toBeEnabled());
    vi.useRealTimers();
  });

  it('tells the learner there is no time limit', () => {
    setup(profileWith({ input_channels: ['text'] }));
    expect(screen.getByText(/no time limit/i)).toBeInTheDocument();
  });
});

describe('authoring failures', () => {
  it('explains itself when no input mode is usable, and blames itself', () => {
    const speechOnly: ContentBlock = {
      ...block,
      interaction: { ...block.interaction, accepted_input_modes: ['speech'] },
    };

    setup(profileWith({ input_channels: ['aac'] }), speechOnly);

    // Scoped to the input, not `getByRole('alert')` globally — the Announcer's
    // assertive live region is also role="alert", correctly so.
    const input = screen.getByTestId('modality-input');
    expect(input).toHaveAttribute('data-state', 'no-usable-input');
    expect(input).toHaveTextContent(/cannot be answered in a way that works for you/);
    expect(input).toHaveTextContent(/our mistake, not yours/);
  });
});

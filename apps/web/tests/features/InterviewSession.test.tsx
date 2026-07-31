/**
 * The mock interview screen.
 *
 * The gateway is stubbed. These tests are about what the SCREEN promises a
 * learner — no timer, pause always available, strengths before improvements,
 * and an honest message when something is down.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { InterviewSession } from '@/features/interview/InterviewSession';
import { CapabilitiesProvider, NO_CAPABILITIES } from '@/services/capabilities';

const PROFILE = {
  user_id: 'p5',
  version: 1,
  input_channels: ['text'],
  output_channels: ['captioned_text'],
  text_complexity: 'standard',
  speech_status: 'atypical',
} as CommunicationAbilityProfile;

function question(n: number, finished = false) {
  return {
    conversation_id: 'iv_test',
    block: {
      id: `interview.hr.q${n}`,
      kind: 'interview_question',
      canonical_text: `Question number ${n}?`,
      intent: 'self_advocacy',
      difficulty: 3,
      representations: { caption: `Question number ${n}?`, easy_read: `Question ${n}.` },
      interaction: { accepted_input_modes: ['speech', 'text', 'aac', 'switch'] },
      a11y: { requires_audio: false, requires_vision: false, requires_speech: false },
      version: 1,
    },
    generated: false,
    provider: 'scripted',
    finished,
    progress: `Question ${n} of about 10`,
  };
}

const SCORE = {
  scored: true,
  dimensions: [{ name: 'content_relevance', score: 4 }],
  strengths: ['You gave a concrete example.'],
  improvements: ['Add the result at the end.', 'Name the team you worked with.'],
  unavailable_message: '',
  audit_id: 'aud_1',
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) => {
    const path = String(url);
    const body = path.includes('/interview/start')
      ? question(1)
      : path.includes('/answer')
        ? question(2)
        : path.includes('/score')
          ? SCORE
          : path.includes('/pause')
            ? { status: 'paused', message: 'Paused. Your place is saved.' }
            : {};
    return { ok: true, status: 200, json: async () => body } as Response;
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

function setup() {
  render(
    <CapabilitiesProvider initial={NO_CAPABILITIES}>
      <AnnouncerProvider>
        <ProfileProvider initialProfile={PROFILE}>
          <InterviewSession userId="p5" />
        </ProfileProvider>
      </AnnouncerProvider>
    </CapabilitiesProvider>,
  );
  return userEvent.setup();
}

async function startInterview(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /start the interview/i }));
  await waitFor(() => expect(screen.getByText('Question number 1?')).toBeInTheDocument());
}

describe('setup', () => {
  it('says up front that nothing is timed and you can stop', async () => {
    setup();
    const intro = screen.getByText(/nobody is watching/i);
    expect(intro).toHaveTextContent(/nothing is timed/i);
    expect(intro).toHaveTextContent(/stop at any question/i);
  });

  it('offers a patient interviewer as the default', () => {
    setup();
    expect(screen.getByRole('radio', { name: /patient/i })).toBeChecked();
  });

  it('uses real radio inputs, so keyboard and voice control work', () => {
    setup();
    expect(screen.getAllByRole('radio').length).toBeGreaterThan(3);
  });
});

describe('answering', () => {
  it('renders the question through the Modality Router', async () => {
    const user = setup();
    await startInterview(user);

    // The router chose captioned_text from the profile; the feature never did.
    expect(screen.getByTestId('modality-router')).toHaveAttribute(
      'data-primary-channel',
      'captioned_text',
    );
  });

  it('advances to the next question when an answer is sent', async () => {
    const user = setup();
    await startInterview(user);

    await user.type(screen.getByLabelText('Your answer'), 'I am consistent.');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    await waitFor(() => expect(screen.getByText('Question number 2?')).toBeInTheDocument());
  });

  it('shows progress as orientation, never as a countdown', async () => {
    const user = setup();
    await startInterview(user);

    const progress = screen.getByText(/Question 1 of about 10/);
    for (const word of ['remaining', 'left', 'seconds', 'minutes', 'hurry']) {
      expect(progress.textContent?.toLowerCase()).not.toContain(word);
    }
  });

  it('offers pause on every question', async () => {
    const user = setup();
    await startInterview(user);

    expect(screen.getByRole('button', { name: /pause/i })).toBeEnabled();
  });

  it('pausing confirms the place is saved and offers to carry on', async () => {
    const user = setup();
    await startInterview(user);

    await user.click(screen.getByRole('button', { name: /pause/i }));

    // Scoped to the heading: the Announcer also speaks this sentence, so a bare
    // text query matches twice.
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /^paused$/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: /carry on/i })).toBeInTheDocument();
  });
});

describe('feedback', () => {
  it('leads with strengths', async () => {
    const user = setup();
    await startInterview(user);

    await user.type(screen.getByLabelText('Your answer'), 'I check every order.');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    const panel = await screen.findByRole('region', { name: /about that answer/i });
    const headings = within(panel).getAllByRole('heading');
    expect(headings[1]).toHaveTextContent(/what worked/i);
  });

  it('shows at most two improvement points', async () => {
    /** More is not more helpful; it is demoralising and unusable. */
    const user = setup();
    await startInterview(user);

    await user.type(screen.getByLabelText('Your answer'), 'ok');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    const panel = await screen.findByRole('region', { name: /about that answer/i });
    const lists = within(panel).getAllByRole('list');
    expect(lists[lists.length - 1]!.querySelectorAll('li').length).toBeLessThanOrEqual(2);
  });

  it('says the score is about what was said, not how', async () => {
    const user = setup();
    await startInterview(user);

    await user.type(screen.getByLabelText('Your answer'), 'ok');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    expect(
      await screen.findByText(/what you said, not how you said it/i),
    ).toBeInTheDocument();
  });
});

describe('when the service is down', () => {
  it('explains rather than showing a blank screen', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        detail: {
          error: 'genai_unavailable',
          message: 'Practice conversations are resting. Everything else still works.',
        },
      }),
    } as Response);

    const user = setup();
    await user.click(screen.getByRole('button', { name: /start the interview/i }));

    expect(await screen.findByTestId('error-note')).toHaveTextContent(/still works/i);
  });

  it('never blames the learner', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: { message: 'Practice conversations are resting.' } }),
    } as Response);

    const user = setup();
    await user.click(screen.getByRole('button', { name: /start the interview/i }));

    const text = (await screen.findByTestId('error-note')).textContent?.toLowerCase() ?? '';
    for (const word of ['invalid', 'you must', 'wrong', 'failed to']) {
      expect(text).not.toContain(word);
    }
  });

  it('keeps the interview usable when only scoring fails', async () => {
    /** A scoring outage must not end someone's interview. */
    fetchMock.mockImplementation(async (url: string) => {
      const path = String(url);
      if (path.includes('/score')) {
        return { ok: false, status: 503, json: async () => ({ detail: {} }) } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => (path.includes('/answer') ? question(2) : question(1)),
      } as Response;
    });

    const user = setup();
    await startInterview(user);

    await user.type(screen.getByLabelText('Your answer'), 'answer');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    await waitFor(() => expect(screen.getByText('Question number 2?')).toBeInTheDocument());
  });
});

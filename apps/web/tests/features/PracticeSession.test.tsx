/**
 * The daily practice loop.
 *
 * This is the screen a learner opens most, so the Charter's copy rules bite
 * hardest here. Most of these tests are about what the screen is allowed to
 * say, not about what it computes.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CommunicationAbilityProfile, ContentBlock } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { PracticeSession } from '@/features/practice/PracticeSession';
import { matches, normaliseAnswer } from '@/features/practice/grading';
import { CapabilitiesProvider, NO_CAPABILITIES } from '@/services/capabilities';

const PROFILE = {
  user_id: 'p5',
  version: 1,
  input_channels: ['text'],
  output_channels: ['captioned_text'],
  text_complexity: 'standard',
  speech_status: 'atypical',
} as CommunicationAbilityProfile;

const BLOCKS: ContentBlock[] = [
  {
    id: 'phrase.greetings.good_morning_01',
    kind: 'phrase',
    canonical_text: 'Good morning.',
    intent: 'greeting',
    difficulty: 1,
    representations: { caption: 'Good morning.', easy_read: 'I say good morning.' },
    interaction: { accepted_input_modes: ['speech', 'text', 'aac', 'switch'] },
    a11y: { requires_audio: false, requires_vision: false, requires_speech: false },
    version: 1,
  } as ContentBlock,
];

interface StubSession {
  items: { block_id: string; canonical_text: string; difficulty: number; is_new: boolean }[];
  estimated_seconds: number;
  note: string | null;
}

const SESSION: StubSession = {
  items: [
    {
      block_id: 'phrase.greetings.good_morning_01',
      canonical_text: 'Good morning.',
      difficulty: 1,
      is_new: true,
    },
  ],
  estimated_seconds: 30,
  note: null,
};

function stubApi(session = SESSION, review = { grade_label: 'Good', interval_days: 1, message: 'Well done. See you again tomorrow.' }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () => (String(url).includes('/review') ? review : session),
    })),
  );
}

function setup() {
  render(
    <CapabilitiesProvider initial={NO_CAPABILITIES}>
      <AnnouncerProvider>
        <ProfileProvider initialProfile={PROFILE}>
          <PracticeSession token="tok" blocks={BLOCKS} />
        </ProfileProvider>
      </AnnouncerProvider>
    </CapabilitiesProvider>,
  );
  return userEvent.setup();
}

beforeEach(() => stubApi());
afterEach(() => vi.unstubAllGlobals());

describe('answer matching', () => {
  it('ignores case, punctuation and spacing', () => {
    expect(matches('good morning', 'Good morning.')).toBe(true);
    expect(matches('  GOOD   MORNING!  ', 'Good morning.')).toBe(true);
  });

  it('forgives articles an AAC board routinely drops', () => {
    /** Composing "the" from symbols is work that says nothing about whether
     *  the learner knows the phrase. */
    expect(matches('I finished first batch', 'I have finished the first batch')).toBe(false);
    expect(matches('I have finished first batch', 'I have finished the first batch')).toBe(true);
  });

  it('forgives fillers that ASR transcribes literally', () => {
    expect(matches('um good morning', 'Good morning.')).toBe(true);
  });

  it('treats contractions and their expansions as the same', () => {
    expect(matches("I'm Ravi", 'I am Ravi')).toBe(true);
  });

  it('still cares about word choice and order', () => {
    /** Those are the thing being learned. */
    expect(matches('morning good', 'Good morning.')).toBe(false);
    expect(matches('good evening', 'Good morning.')).toBe(false);
  });

  it('normalises to something stable and comparable', () => {
    expect(normaliseAnswer("Could you PLEASE repeat that?")).toBe('could you please repeat that');
  });
});

describe('the session', () => {
  it('shows the phrase through the Modality Router', async () => {
    setup();

    await waitFor(() =>
      expect(screen.getByTestId('modality-router')).toHaveAttribute(
        'data-primary-channel',
        'captioned_text',
      ),
    );
  });

  it('shows position as orientation, never as a countdown', async () => {
    setup();

    const progress = await screen.findByText('1 of 1');
    for (const word of ['remaining', 'left', 'seconds', 'hurry', 'streak']) {
      expect(progress.textContent?.toLowerCase()).not.toContain(word);
    }
  });

  it('records an answer and shows the encouraging message', async () => {
    const user = setup();
    await screen.findByLabelText('Your answer');

    await user.type(screen.getByLabelText('Your answer'), 'Good morning');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    // Scoped to the feedback panel: the Announcer speaks the same sentence, so
    // a bare text query matches twice.
    const feedback = await screen.findByRole('region', { name: /how that went/i });
    expect(within(feedback).getByText(/well done/i)).toBeInTheDocument();
  });

  it('never says "wrong", "failed" or "incorrect"', async () => {
    /** The Charter's copy rules apply hardest to the string a learner reads
     *  most often. "Not quite yet" is the strongest negative we own. */
    stubApi(SESSION, {
      grade_label: 'Again',
      interval_days: 1,
      message: 'Not quite yet. We will come back to this one soon.',
    });
    const user = setup();
    await screen.findByLabelText('Your answer');

    await user.type(screen.getByLabelText('Your answer'), 'Good evening');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    const feedback = await screen.findByRole('region', { name: /how that went/i });
    expect(within(feedback).getByText(/not quite yet/i)).toBeInTheDocument();

    const page = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['wrong', 'incorrect', 'failed', 'error']) {
      expect(page).not.toContain(word);
    }
  });

  it('offers another go rather than showing the grade "Again"', async () => {
    /** FSRS's lowest grade is called Again. The learner is never shown that
     *  word — they are offered another attempt, which is the same information
     *  without the verdict. */
    stubApi(SESSION, {
      grade_label: 'Again',
      interval_days: 1,
      message: 'Not quite yet. We will come back to this one soon.',
    });
    const user = setup();
    await screen.findByLabelText('Your answer');

    await user.type(screen.getByLabelText('Your answer'), 'nope');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    expect(await screen.findByRole('button', { name: /try that again/i })).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('Again.');
  });

  it('frames an empty session as finishing, not as a dead end', async () => {
    stubApi({ items: [], estimated_seconds: 0, note: 'That is everything ready for you today.' });
    setup();

    expect(await screen.findByText(/nothing due right now/i)).toBeInTheDocument();
    expect(screen.getByText(/everything ready for you today/i)).toBeInTheDocument();
  });

  it('celebrates the end of a session without a streak or a score', async () => {
    const user = setup();
    await screen.findByLabelText('Your answer');

    await user.type(screen.getByLabelText('Your answer'), 'Good morning');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));
    await user.click(await screen.findByRole('button', { name: 'Next' }));

    expect(await screen.findByText(/that is your practice done/i)).toBeInTheDocument();
    const page = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['streak', 'score', '%', 'points']) {
      expect(page).not.toContain(word);
    }
  });
});

describe('when saving fails', () => {
  it('keeps the learner’s place rather than losing the answer', async () => {
    const user = setup();
    await screen.findByLabelText('Your answer');

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 503, json: async () => ({}) })),
    );

    await user.type(screen.getByLabelText('Your answer'), 'Good morning');
    await user.click(screen.getByRole('button', { name: 'Send answer' }));

    expect(await screen.findByTestId('practice-error')).toHaveTextContent(/your place is kept/i);
  });
});

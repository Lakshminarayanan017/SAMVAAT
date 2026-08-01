/**
 * The progress screen.
 *
 * Motivation UI is where accessibility gets betrayed most casually. These tests
 * are mostly about what the screen is forbidden from saying.
 */
import { render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProgressPanel, type Badge, type Progress, type Suggestion } from '@/features/progress/ProgressPanel';
import { page } from '../helpers';

const PROGRESS: Progress = {
  xp: 240,
  days_practised: 12,
  current_run: 4,
  longest_run: 9,
  summary: '4 days in a row, and 12 days altogether.',
  phrases_started: 30,
  phrases_reliable: 8,
  interviews_completed: 2,
  badges: [
    {
      id: 'first_practice',
      family: 'consistency',
      label: 'First practice',
      earned_message: 'You started. That is the hardest part.',
    },
  ],
};

const ALL_BADGES: Badge[] = [
  PROGRESS.badges[0]!,
  {
    id: 'disclosure_rehearsed',
    family: 'courage',
    label: 'Asked for what you need',
    earned_message: 'You rehearsed asking for an adjustment.',
  },
  {
    id: 'own_best',
    family: 'growth',
    label: 'Your best yet',
    earned_message: 'Your best result so far — measured against you, nobody else.',
  },
];

const NEXT: Suggestion[] = [
  {
    block_id: 'phrase.clarification.repeat_request_01',
    canonical_text: 'Could you please repeat that?',
    explanation: 'The /r/ sound has been tricky this week.',
    reason: 'weak_sound',
  },
];

function stubApi(progress = PROGRESS, badges = ALL_BADGES, next = NEXT, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const path = String(url);
      const body = path.includes('/badges') ? badges : path.includes('/next') ? next : progress;
      return { ok, status: ok ? 200 : 503, json: async () => body };
    }),
  );
}

function setup() {
  render(
    <AnnouncerProvider>
      <ProgressPanel token="tok" />
    </AnnouncerProvider>,
  );
}

beforeEach(() => stubApi());
afterEach(() => vi.unstubAllGlobals());

describe('the headline', () => {
  it('leads with days practised, which only goes up', async () => {
    setup();
    // Scoped to the page: the summary is also announced, so an unscoped query
    // finds two copies of it.
    expect(await page().findByText(/12 days altogether/)).toBeInTheDocument();
  });

  it('never frames a streak as at risk', async () => {
    setup();
    await page().findByText(/12 days altogether/);

    const text = document.body.textContent?.toLowerCase() ?? '';
    // The punitive framings, not the bare words — the screen legitimately says
    // "nothing here expires", which is the opposite of a threat.
    for (const phrase of [
      'at risk',
      'keep your streak',
      'will expire',
      'expires soon',
      'streak lost',
      'you lost',
      'days left',
    ]) {
      expect(text).not.toContain(phrase);
    }
  });

  it('says effort points are for trying, not for being right', async () => {
    setup();
    expect(await page().findByText(/for trying, not for being right/i)).toBeInTheDocument();
  });

  it('labels every number for a screen reader', async () => {
    /** A bare "240" in a box means nothing without its label read alongside. */
    setup();
    await page().findByText(/12 days altogether/);

    expect(page().getByText(/Effort points: 240\./)).toBeInTheDocument();
    expect(page().getByText(/Phrases started: 30\./)).toBeInTheDocument();
  });

  it('never compares the learner to anyone else', async () => {
    setup();
    await page().findByText(/12 days altogether/);

    const text = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['percentile', 'rank', 'leaderboard', 'average learner', 'top 10']) {
      expect(text).not.toContain(word);
    }
  });
});

describe('what to try next', () => {
  it('shows the reason alongside every suggestion', async () => {
    setup();
    expect(await screen.findByText('The /r/ sound has been tricky this week.')).toBeInTheDocument();
  });

  it('shows the API wording verbatim rather than re-deriving it', async () => {
    /** One wording, in one place, testable. */
    stubApi(PROGRESS, ALL_BADGES, [
      { ...NEXT[0]!, explanation: 'This comes up in the warehouse.' },
    ]);
    setup();

    expect(await screen.findByText('This comes up in the warehouse.')).toBeInTheDocument();
  });
});

describe('badges', () => {
  it('shows the whole set, not only what has been earned', async () => {
    /** Hidden goals are a dark pattern; visible ones are direction. */
    setup();

    expect(await screen.findByText('Asked for what you need')).toBeInTheDocument();
    expect(screen.getByText('Your best yet')).toBeInTheDocument();
  });

  it('marks unearned badges in words, not only by opacity', async () => {
    /** Greying something out tells a screen-reader user nothing at all. */
    setup();
    await screen.findByText('Asked for what you need');

    expect(screen.getByText(/— earned/)).toBeInTheDocument();
    expect(screen.getAllByText(/— not earned yet/).length).toBeGreaterThan(0);
  });

  it('groups badges by what they are for', async () => {
    setup();

    expect(await screen.findByRole('heading', { name: /hard conversations/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /your own progress/i })).toBeInTheDocument();
  });

  it('never presents an unearned badge as a failure', async () => {
    setup();
    await screen.findByText('Asked for what you need');

    const text = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['locked', 'missed', 'failed', 'you have not', 'incomplete']) {
      expect(text).not.toContain(word);
    }
  });

  it('says nothing expires', async () => {
    setup();
    expect(await screen.findByText(/nothing here expires/i)).toBeInTheDocument();
  });

  it('keeps the growth badge measured against the learner', async () => {
    setup();
    const growth = await screen.findByText(/measured against you, nobody else/i);
    expect(growth).toBeInTheDocument();
  });
});

describe('when the API is unreachable', () => {
  it('explains rather than showing a zeroed dashboard', async () => {
    /** A screen full of zeros would read as "you have done nothing", which is
     *  a very different and much crueller statement than "we could not load". */
    stubApi(PROGRESS, ALL_BADGES, NEXT, false);
    setup();

    expect(await screen.findByTestId('progress-error')).toHaveTextContent(/could not load/i);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});

describe('empty state', () => {
  it('welcomes a brand-new learner without implying failure', async () => {
    stubApi(
      {
        ...PROGRESS,
        xp: 0,
        days_practised: 0,
        current_run: 0,
        longest_run: 0,
        summary: 'Your first practice. Welcome.',
        phrases_started: 0,
        phrases_reliable: 0,
        interviews_completed: 0,
        badges: [],
      },
      ALL_BADGES,
      [],
    );
    setup();

    expect(await page().findByText(/your first practice\. welcome\./i)).toBeInTheDocument();

    const badges = screen.getByRole('heading', { name: /^badges$/i });
    expect(badges).toBeInTheDocument();
    // Every badge is still shown, as a map of what exists.
    expect(within(document.body).getAllByText(/— not earned yet/).length).toBe(ALL_BADGES.length);
  });
});

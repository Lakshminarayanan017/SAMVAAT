/**
 * The trainer dashboard.
 *
 * Two properties matter more than the layout: a learner who has not shared is
 * shown honestly rather than hidden, and the cohort is real tabular data so a
 * screen-reader user hears "Ravi, due today, 4" instead of a stream of numbers.
 * Trainers are disabled people too.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { TrainerDashboard, type CohortMember } from '@/features/trainer/TrainerDashboard';

function member(overrides: Partial<CohortMember> = {}): CohortMember {
  return {
    learner_user_id: 'gst_1',
    display_name: 'Ravi',
    shared: true,
    cards_started: 12,
    cards_due: 4,
    lapses: 2,
    interviews_completed: 1,
    last_active_at: '2026-07-30T09:00:00Z',
    is_active: true,
    ...overrides,
  };
}

const AGREEMENT = {
  scores: 10,
  overridden: 1,
  agreement: 0.9,
  target_agreement: 0.85,
  note: 'Below 85% agreement, the scoring needs work — not the trainers.',
};

function stubApi(cohort: CohortMember[], agreement = AGREEMENT, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => ({
      ok,
      status: ok ? 200 : 503,
      json: async () => (String(url).includes('/agreement') ? agreement : cohort),
    })),
  );
}

function setup() {
  render(
    <AnnouncerProvider>
      <TrainerDashboard token="trainer-token" />
    </AnnouncerProvider>,
  );
}

beforeEach(() => stubApi([member()]));
afterEach(() => vi.unstubAllGlobals());

describe('the cohort', () => {
  it('presents learners as a real table, not a grid of divs', async () => {
    /** So a screen reader can navigate by column and announce each cell with
     *  its heading, rather than reading an unlabelled stream of numbers. */
    setup();

    const table = await screen.findByRole('table');
    expect(within(table).getByRole('columnheader', { name: /due today/i })).toBeInTheDocument();
    expect(within(table).getByRole('rowheader', { name: 'Ravi' })).toBeInTheDocument();
  });

  it('shows a shared learner their metrics', async () => {
    setup();

    const row = await screen.findByRole('row', { name: /Ravi/ });
    expect(within(row).getByText('12')).toBeInTheDocument();
    expect(within(row).getByText('4')).toBeInTheDocument();
  });

  it('shows a learner who has not shared, rather than hiding them', async () => {
    /** They are on this trainer's caseload. Hiding them would be dishonest. */
    stubApi([
      member({
        display_name: 'Meena',
        shared: false,
        cards_started: null,
        cards_due: null,
        lapses: null,
        interviews_completed: null,
        last_active_at: null,
      }),
    ]);
    setup();

    const row = await screen.findByRole('row', { name: /Meena/ });
    expect(within(row).getByText('Not yet')).toBeInTheDocument();
  });

  it('says "not shared" in words, not only as a dash', async () => {
    stubApi([
      member({
        shared: false,
        cards_started: null,
        cards_due: null,
        lapses: null,
        interviews_completed: null,
        last_active_at: null,
      }),
    ]);
    setup();

    await screen.findByRole('table');
    // A bare em dash tells a screen-reader user nothing at all.
    expect(screen.getAllByText('Not shared').length).toBeGreaterThan(0);
  });

  it('counts how many are still waiting to share', async () => {
    stubApi([
      member(),
      member({
        learner_user_id: 'gst_2',
        display_name: 'Meena',
        shared: false,
        cards_started: null,
        cards_due: null,
        lapses: null,
        interviews_completed: null,
        last_active_at: null,
      }),
    ]);
    setup();

    expect(await screen.findByText(/not sharing their progress yet/i)).toBeInTheDocument();
  });

  it('explains an empty caseload rather than showing a bare table', async () => {
    stubApi([]);
    setup();

    expect(await screen.findByText(/nobody on your caseload yet/i)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('never ranks learners against each other', async () => {
    /** A trainer needs to see who might need attention today. A league table of
     *  disabled learners is a different thing, and we are not building it. */
    stubApi([member(), member({ learner_user_id: 'gst_2', display_name: 'Meena' })]);
    setup();

    await screen.findByRole('table');
    const page = document.body.textContent?.toLowerCase() ?? '';
    for (const word of ['rank', 'leaderboard', 'top performer', 'worst', 'best learner']) {
      expect(page).not.toContain(word);
    }
  });
});

describe('agreement with the AI', () => {
  it('shows the counts behind the percentage', async () => {
    /** A percentage alone means little; 90% of ten is not 90% of a thousand. */
    setup();

    expect(await screen.findByText('90%')).toBeInTheDocument();
    expect(screen.getByText(/accepted 9 of 10 scores/i)).toBeInTheDocument();
  });

  it('blames the scoring, not the trainer, when agreement is low', async () => {
    stubApi([member()], { ...AGREEMENT, agreement: 0.5, overridden: 5 });
    setup();

    expect(await screen.findByText(/below the 85% target/i)).toBeInTheDocument();
    expect(screen.getByText(/not the trainers/i)).toBeInTheDocument();
  });

  it('says so plainly when there is nothing to measure yet', async () => {
    stubApi([member()], { ...AGREEMENT, scores: 0, overridden: 0, agreement: 1 });
    setup();

    expect(await screen.findByText(/no scores yet/i)).toBeInTheDocument();
  });
});

describe('when the API is unreachable', () => {
  it('explains rather than showing an empty caseload', async () => {
    /** An empty table would read as "you have no learners", which is a very
     *  different and much more alarming statement than "we could not load". */
    stubApi([], AGREEMENT, false);
    setup();

    await waitFor(() =>
      expect(screen.getByTestId('trainer-error')).toHaveTextContent(/could not load/i),
    );
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});

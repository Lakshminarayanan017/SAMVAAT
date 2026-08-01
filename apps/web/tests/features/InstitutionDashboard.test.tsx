/**
 * The institution dashboard.
 *
 * The API already refuses to publish an unsafe figure — that is tested there.
 * What is tested here is the other failure mode, which is entirely a UI problem:
 * a suppressed cell rendered as a blank, or worse as a zero, reads as a bug.
 * An institution that thinks it is a bug asks us to remove the protection.
 *
 * So: every withheld cell must carry its reason, and no withheld cell may ever
 * show a number.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import {
  InstitutionDashboard,
  type Cell,
  type CohortReport,
} from '@/features/institution/InstitutionDashboard';
import { page } from '../helpers';

const WITHHELD = 'Withheld: fewer than 5 learners, so a figure here could identify someone.';

function shown(label: string, count: number): Cell {
  return { label, count, suppressed: false, reason: '' };
}

function hidden(label: string): Cell {
  return { label, count: null, suppressed: true, reason: WITHHELD };
}

function report(overrides: Partial<CohortReport> = {}): CohortReport {
  return {
    learners: shown('learners', 40),
    enrolled: 44,
    active_last_30_days: shown('active', 28),
    completed_an_interview: shown('interviewed', 19),
    reliable_phrases: {
      '0-9': shown('0-9', 22),
      '10-49': shown('10-49', 11),
      '50+': shown('50+', 7),
    },
    modality_mix: {
      captioned_text: shown('captioned_text', 22),
      audio: shown('audio', 11),
      easy_read: shown('easy_read', 7),
    },
    engagement_rate: 70,
    notes: ['Figures are withheld wherever fewer than 5 learners are involved.'],
    ...overrides,
  };
}

function stubApi(body: CohortReport, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok, status: ok ? 200 : 503, json: async () => body })),
  );
}

function setup() {
  render(
    <AnnouncerProvider>
      <InstitutionDashboard token="institution-token" />
    </AnnouncerProvider>,
  );
}

beforeEach(() => stubApi(report()));
afterEach(() => vi.unstubAllGlobals());

describe('the headline figures', () => {
  it('shows the cohort size', async () => {
    setup();
    await waitFor(() => expect(page().getByText('40')).toBeInTheDocument());
  });

  it('shows enrolment separately from consent, so the gap is visible', async () => {
    setup();
    // 44 enrolled, 40 consenting. An institution is entitled to know four of
    // its own learners declined — but not which four.
    await waitFor(() => expect(page().getByText('44')).toBeInTheDocument());
    expect(page().getByText('40')).toBeInTheDocument();
  });

  it('renders the engagement rate as a percentage', async () => {
    setup();
    await waitFor(() => expect(page().getByText('70%')).toBeInTheDocument());
  });
});

describe('withheld figures', () => {
  it('never prints a number for a suppressed cell', async () => {
    stubApi(report({ learners: hidden('learners'), active_last_30_days: hidden('active') }));
    setup();

    await waitFor(() => expect(page().getAllByText(WITHHELD).length).toBeGreaterThan(0));
    // Nothing in the document claims a count for a withheld cell.
    expect(page().queryByText('40')).not.toBeInTheDocument();
    expect(page().queryByText('28')).not.toBeInTheDocument();
  });

  it('never substitutes a zero for a withheld count', async () => {
    /* A zero is itself a fact about a small group — "0 learners here use ISL"
       plus a roster is as identifying as a name. */
    stubApi(report({ completed_an_interview: hidden('interviewed') }));
    setup();

    await waitFor(() => expect(page().getByText(WITHHELD)).toBeInTheDocument());
    expect(page().queryByText('0')).not.toBeInTheDocument();
  });

  it('explains every gap in words, not as an empty space', async () => {
    stubApi(
      report({
        modality_mix: { captioned_text: hidden('captioned_text'), isl: hidden('isl') },
      }),
    );
    setup();

    await waitFor(() => expect(page().getAllByText(WITHHELD)).toHaveLength(2));
  });

  it('says why the whole report is empty when the cohort is too small', async () => {
    const tooSmall = 'Fewer than 5 learners have agreed to be included.';
    stubApi(
      report({
        learners: hidden('learners'),
        reliable_phrases: {},
        modality_mix: {},
        engagement_rate: null,
        notes: [tooSmall],
      }),
    );
    setup();

    await waitFor(() => expect(page().getByText(tooSmall)).toBeInTheDocument());
  });

  it('explains a withheld engagement rate rather than showing nothing', async () => {
    stubApi(report({ engagement_rate: null }));
    setup();

    await waitFor(() =>
      expect(page().getAllByText(/too small to publish a rate/i).length).toBeGreaterThan(0),
    );
  });

  it('reads the reason to a screen reader exactly once', async () => {
    /* The visible reason is aria-hidden and the same words are folded into the
       figure's spoken sentence. Rendering both into the accessibility tree
       makes a screen reader say the whole explanation twice. */
    stubApi(report({ engagement_rate: null }));
    setup();

    await waitFor(() => expect(page().getByText('40')).toBeInTheDocument());

    const spoken = Array.from(
      document.querySelectorAll('[data-samvaad-content] .visually-hidden'),
    ).filter((node) => /too small to publish a rate/i.test(node.textContent ?? ''));

    expect(spoken).toHaveLength(1);
  });
});

describe('what a screen reader hears', () => {
  it('reads a withheld cell as withheld, not as a dash', async () => {
    /* The visible "—" is aria-hidden. Somebody using a screen reader must hear
       the same fact a sighted user reads, not a punctuation mark. */
    stubApi(report({ learners: hidden('learners') }));
    setup();

    await waitFor(() =>
      expect(
        page().getByText(/included in reporting: withheld/i, { selector: 'span' }),
      ).toBeInTheDocument(),
    );
  });

  it('gives the breakdowns real table semantics', async () => {
    setup();
    await waitFor(() => expect(page().getAllByRole('table')).toHaveLength(2));
    // Row headers, so a screen reader says "Indian Sign Language, 7" rather
    // than reading a bare column of numbers.
    expect(page().getAllByRole('rowheader').length).toBeGreaterThan(0);
  });

  it('names the modality codes in plain language', async () => {
    setup();
    await waitFor(() => expect(page().getByText('Text and captions')).toBeInTheDocument());
    expect(page().getByText('Easy-Read')).toBeInTheDocument();
  });
});

describe('what is never on screen', () => {
  it('offers no control that narrows the cohort', async () => {
    /* Arbitrary filtering is how aggregate data becomes individuals. There is
       no filter in the API, so there must be none in the UI inviting one. */
    setup();
    await waitFor(() => expect(page().getByText('40')).toBeInTheDocument());

    expect(page().queryAllByRole('combobox')).toHaveLength(0);
    expect(page().queryAllByRole('textbox')).toHaveLength(0);
    expect(page().queryAllByRole('searchbox')).toHaveLength(0);
  });

  it('offers no drill-down into a single learner', async () => {
    setup();
    await waitFor(() => expect(page().getByText('40')).toBeInTheDocument());

    expect(page().queryAllByRole('link')).toHaveLength(0);
    expect(page().queryAllByRole('button')).toHaveLength(0);
  });
});

describe('when the report cannot be loaded', () => {
  it('says so plainly instead of rendering an empty report', async () => {
    /* An empty report and a failed request look identical, and one of them
       would be read as "nobody is using it". */
    stubApi(report(), false);
    setup();

    await waitFor(() =>
      expect(screen.getByTestId('institution-error')).toHaveTextContent(/could not load/i),
    );
  });
});

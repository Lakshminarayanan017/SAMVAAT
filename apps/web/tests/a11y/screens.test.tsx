/**
 * Automated accessibility conformance — the real screens.
 *
 * accessibility.test.tsx sweeps every channel and input mode through the
 * Modality Router. That proves the router is clean; it proves nothing about the
 * screens built around it, which is where the tables, live regions, tab lists
 * and status banners actually live — and where axe violations actually happen.
 *
 * Every learner- or staff-facing surface goes through here. A screen added
 * without a row in this file is a screen nobody has checked.
 *
 * axe catches roughly a third of real barriers. This is a floor, not a pass:
 * the manual screen-reader passes tracked in docs/STATUS.md (M18) are what
 * would actually clear this product, and they have not happened yet.
 */
import { render, waitFor } from '@testing-library/react';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import type { CommunicationAbilityProfile } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { InstitutionDashboard } from '@/features/institution/InstitutionDashboard';
import { ProgressPanel } from '@/features/progress/ProgressPanel';
import { SocialStory } from '@/features/stories/SocialStory';
import { StoryChooser } from '@/features/stories/StoryChooser';
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { CapabilitiesProvider, NO_CAPABILITIES } from '@/services/capabilities';

import { blockingViolations, checkA11y, formatViolations } from './axe';

/**
 * The hardest profile to serve, used everywhere here on purpose.
 *
 * Symbols plus Easy-Read plus switch access exercises more of the a11y surface
 * than a default profile does, and a screen that is clean for P4 and P2
 * together is usually clean for everyone.
 */
const HARDEST: CommunicationAbilityProfile = {
  user_id: 'axe-screens',
  version: 1,
  input_channels: ['switch'],
  output_channels: ['easy_read', 'pictograph'],
  text_complexity: 'easy_read',
  speech_status: 'nonverbal',
} as CommunicationAbilityProfile;

function shell(children: React.ReactNode) {
  return render(
    <CapabilitiesProvider initial={NO_CAPABILITIES}>
      <AnnouncerProvider>
        <ProfileProvider initialProfile={HARDEST}>
          <main>{children}</main>
        </ProfileProvider>
      </AnnouncerProvider>
    </CapabilitiesProvider>,
  );
}

async function expectClean(container: Element) {
  const results = await checkA11y(container);
  const blocking = blockingViolations(results);
  expect(blocking, formatViolations({ ...results, violations: blocking })).toHaveLength(0);
}

function stub(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok: true, status: 200, json: async () => body })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('the institution dashboard', () => {
  const suppressed = {
    label: '',
    count: null,
    suppressed: true,
    reason: 'Withheld: fewer than 5 learners.',
  };

  beforeEach(() =>
    stub({
      learners: { label: 'learners', count: 40, suppressed: false, reason: '' },
      enrolled: 44,
      active_last_30_days: { label: 'active', count: 28, suppressed: false, reason: '' },
      completed_an_interview: suppressed,
      reliable_phrases: {
        '0-9': { label: '0-9', count: 22, suppressed: false, reason: '' },
        '50+': suppressed,
      },
      modality_mix: { isl: suppressed },
      engagement_rate: 70,
      notes: ['Figures are withheld wherever fewer than 5 learners are involved.'],
    }),
  );

  it('is clean, including its suppressed cells', async () => {
    // Suppressed cells are the interesting case: they carry aria-hidden
    // markers and visually-hidden text, which is where axe tends to bite.
    const { container } = shell(<InstitutionDashboard token="t" />);
    await waitFor(() => expect(container.querySelectorAll('table')).toHaveLength(2));
    await expectClean(container);
  });
});

describe('the trainer dashboard', () => {
  beforeEach(() =>
    stub([
      {
        learner_user_id: 'gst_1',
        display_name: 'Ravi',
        shared: true,
        cards_started: 12,
        cards_due: 4,
        lapses: 2,
        interviews_completed: 1,
        last_active_at: '2026-07-30T09:00:00Z',
        is_active: true,
      },
    ]),
  );

  it('is clean', async () => {
    const { container } = shell(<TrainerDashboard token="t" />);
    await waitFor(() => expect(container.textContent).toContain('Ravi'));
    await expectClean(container);
  });
});

describe('the progress panel', () => {
  /* Three different endpoints, three different shapes. Stubbing one shape for
     all of them renders an empty panel, and an empty panel passes axe while
     proving nothing. */
  beforeEach(() => {
    const progress = {
      xp: 120,
      days_practised: 3,
      current_run: 3,
      longest_run: 5,
      summary: 'You have practised on three days.',
      phrases_started: 20,
      phrases_reliable: 7,
      interviews_completed: 1,
      badges: [
        {
          id: 'courage.first_interview',
          family: 'courage',
          label: 'First interview',
          earned_message: 'You finished a whole interview.',
        },
      ],
    };
    const badges = [
      {
        id: 'mastery.ten_phrases',
        family: 'mastery',
        label: 'Ten phrases',
        earned_message: 'You know ten phrases well.',
      },
    ];
    const suggestions = [
      {
        block_id: 'phrase.clarify.repeat_request_01',
        canonical_text: 'Could you say that again, please?',
        explanation: 'You found this hard last time.',
        reason: 'recent_difficulty',
      },
    ];

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => ({
        ok: true,
        status: 200,
        json: async () => {
          const path = String(url);
          if (path.includes('/badges')) return badges;
          if (path.includes('/next') || path.includes('recommend')) return suggestions;
          return progress;
        },
      })),
    );
  });

  it('is clean, with badges and suggestions on screen', async () => {
    const { container } = shell(<ProgressPanel token="t" />);
    // Real content, not an empty shell or an error state.
    await waitFor(() => expect(container.textContent).toContain('120'));
    await expectClean(container);
  });
});

describe('social stories', () => {
  it('the chooser is clean before a situation is picked', async () => {
    const { container } = shell(<StoryChooser token="t" />);
    await waitFor(() => expect(container.querySelectorAll('button').length).toBeGreaterThan(0));
    await expectClean(container);
  });

  it('a story being read is clean, provenance banner and all', async () => {
    stub({
      title: 'When my supervisor asks me to do it again',
      panels: [
        { text: 'I work in a stockroom.', type: 'descriptive', pictograph_hint: 'work' },
        { text: 'I can ask what to change.', type: 'directive', pictograph_hint: 'ask' },
      ],
      status: 'draft',
      generated: true,
      validation: { valid: true, problems: [], directive_count: 1, non_directive_count: 1, ratio: 1 },
      notice: null,
    });

    const { container } = shell(
      <SocialStory token="t" jobContext="a stockroom" situation="being asked to redo a task" />,
    );

    const start = container.querySelector('button');
    start?.click();

    await waitFor(() => expect(container.textContent).toContain('stockroom'));
    await expectClean(container);
  });
});

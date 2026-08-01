/**
 * The level runner and the celebration.
 *
 * These test the four rules the runner exists to hold — the end is always
 * visible, nothing is timed, retries cost nothing, a scaffold is always one
 * press away — plus the two things the celebration is easy to get wrong:
 * announcing once rather than three times, and honouring the motion level.
 *
 * The "no timing" and "no loss aversion" tests read the rendered output rather
 * than the source, so copy added later is covered too.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ContentBlock, CommunicationAbilityProfile } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { DEFAULT_PROFILE, ProfileProvider } from '@/a11y/ProfileProvider';
import { Celebration, resolveCelebration } from '@/game/Celebration';
import { LevelRunner, type MissionPlan } from '@/game/LevelRunner';

function block(id: string, text: string): ContentBlock {
  return {
    id,
    kind: 'phrase',
    canonical_text: text,
    intent: 'greeting',
    difficulty: 1,
    representations: { caption: text, easy_read: text },
    interaction: { accepted_input_modes: ['text', 'aac', 'switch', 'speech', 'sign'] },
    a11y: { requires_audio: false, requires_vision: false, requires_speech: false },
    version: 1,
  } as ContentBlock;
}

const BLOCKS = [
  block('p1', 'Good morning'),
  block('p2', 'Good afternoon'),
  block('p3', 'My name is Ravi'),
];

function plan(overrides: Partial<MissionPlan> = {}): MissionPlan {
  return {
    level_id: 'lvl1',
    title: 'First words',
    world_title: 'Finding Your Voice',
    sensitive: false,
    total: 3,
    missions: [
      {
        id: 'm1',
        type: 'recognise',
        block_id: 'p1',
        prompt: 'Which one means the same thing?',
        options: ['Good morning', 'Good afternoon'],
        scaffold: 'The right one says the same thing in different words.',
      },
      {
        id: 'm2',
        type: 'recognise',
        block_id: 'p2',
        prompt: 'Which one means the same thing?',
        options: ['Good afternoon', 'My name is Ravi'],
        scaffold: 'Think about the time of day.',
      },
      {
        id: 'm3',
        type: 'produce',
        block_id: 'p3',
        prompt: 'What would you say?',
        options: [],
        scaffold: 'You can look at the words first.',
      },
    ],
    ...overrides,
  };
}

function shell(ui: React.ReactNode, profile: CommunicationAbilityProfile = DEFAULT_PROFILE) {
  return render(
    <AnnouncerProvider>
      <ProfileProvider initialProfile={profile}>
        <main>{ui}</main>
      </ProfileProvider>
    </AnnouncerProvider>,
  );
}

function ui() {
  return within(document.querySelector('main') as HTMLElement);
}

function runner(props: Partial<React.ComponentProps<typeof LevelRunner>> = {}) {
  return shell(
    <LevelRunner
      plan={plan()}
      blocks={BLOCKS}
      token="t"
      celebrationLevel="gentle"
      onLeave={vi.fn()}
      onNext={vi.fn()}
      {...props}
    />,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ xp_awarded: 10 }) })),
  );
});
afterEach(() => vi.unstubAllGlobals());

async function start() {
  await userEvent.click(ui().getByRole('button', { name: 'Start' }));
}

describe('the intro', () => {
  it('says how many missions there are before the learner commits', async () => {
    /* The end is visible before the beginning. */
    runner();
    expect(ui().getByText(/3 things to try/i)).toBeInTheDocument();
  });

  it('offers a way not to start', async () => {
    const onLeave = vi.fn();
    runner({ onLeave });
    await userEvent.click(ui().getByRole('button', { name: 'Not now' }));
    expect(onLeave).toHaveBeenCalled();
  });

  it('promises nothing is timed, up front', async () => {
    runner();
    expect(ui().getByText(/nothing is timed/i)).toBeInTheDocument();
  });
});

describe('the end is always visible', () => {
  it('shows progress in words on every mission', async () => {
    runner();
    await start();

    expect(ui().getByRole('group', { name: '0 of 3 missions done.' })).toBeInTheDocument();
  });

  it('advances the count as missions are finished', async () => {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: 'Good morning' }));
    await userEvent.click(ui().getByRole('button', { name: 'Next' }));

    expect(ui().getByRole('group', { name: '1 of 3 missions done.' })).toBeInTheDocument();
  });
});

describe('nothing is timed (Ethics E6)', () => {
  it('has no countdown or speed language anywhere in the run', async () => {
    runner();
    await start();

    const text = document.querySelector('main')?.textContent ?? '';
    for (const banned of [
      /seconds? left/i,
      /time remaining/i,
      /countdown/i,
      /hurry/i,
      /too slow/i,
      /be quick/i,
    ]) {
      expect(text).not.toMatch(banned);
    }
  });
});

describe('retries cost nothing', () => {
  it('offers no lives, hearts or energy', async () => {
    runner();
    await start();

    const text = document.querySelector('main')?.textContent ?? '';
    for (const banned of [/lives/i, /hearts/i, /energy/i, /you lost/i, /try again tomorrow/i]) {
      expect(text).not.toMatch(banned);
    }
  });

  it('shows coaching rather than a verdict after a wrong answer', async () => {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: 'Good afternoon' }));

    expect(ui().getByText(/not quite yet/i)).toBeInTheDocument();
    expect(document.querySelector('main')?.textContent).not.toMatch(/wrong|incorrect|failed/i);
  });

  it('names what does fit, rather than leaving the learner where they were', async () => {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: 'Good afternoon' }));
    expect(ui().getByText(/the one that fits is: good morning/i)).toBeInTheDocument();
  });

  it('lets the learner continue after getting it wrong', async () => {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: 'Good afternoon' }));
    expect(ui().getByRole('button', { name: 'Next' })).toBeInTheDocument();
  });
});

describe('a scaffold is always one press away', () => {
  it('offers a hint on every mission', async () => {
    runner();
    await start();
    expect(ui().getByRole('button', { name: /give me a hint/i })).toBeInTheDocument();
  });

  it('shows the hint when asked', async () => {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: /give me a hint/i }));
    expect(ui().getByText(/says the same thing in different words/i)).toBeInTheDocument();
  });

  it('reports the hint to the API so the grade can reflect it', async () => {
    /* Asking for a scaffold is genuine partial recall, so it lowers the FSRS
       grade — and never lowers XP, which is for effort. Both are enforced in
       the API by function signature; the client only reports what happened. */
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: /give me a hint/i }));
    await userEvent.click(ui().getByRole('button', { name: 'Good morning' }));

    const body = JSON.parse(vi.mocked(fetch).mock.calls[0]?.[1]?.body as string);
    expect(body.hints_used).toBe(1);
  });

  it('sends no timing information with an answer', async () => {
    /* Ethics E6 again, from the other side: the API cannot see duration
       because nothing sends it. */
    runner();
    await start();
    await userEvent.click(ui().getByRole('button', { name: 'Good morning' }));

    const body = JSON.parse(vi.mocked(fetch).mock.calls[0]?.[1]?.body as string);
    for (const key of Object.keys(body)) {
      expect(key).not.toMatch(/time|duration|elapsed|seconds|ms$/i);
    }
  });
});

describe('production missions', () => {
  it('let the learner say whether it landed, rather than auto-scoring speech', async () => {
    /* Auto-scoring a spoken answer would put ASR quality between a learner and
       their own progress (ADR-0002). */
    runner({ plan: plan({ missions: [plan().missions[2]!] }) });
    await start();

    expect(ui().getByRole('button', { name: /i said it/i })).toBeInTheDocument();
    expect(ui().getByRole('button', { name: /i need more practice/i })).toBeInTheDocument();
  });

  it('does not treat "I need more practice" as a failure', async () => {
    runner({ plan: plan({ missions: [plan().missions[2]!] }) });
    await start();

    await userEvent.click(ui().getByRole('button', { name: /i need more practice/i }));
    expect(document.querySelector('main')?.textContent).not.toMatch(/wrong|failed/i);
  });
});

describe('leaving', () => {
  it('offers a way out on every mission', async () => {
    /* A learner who cannot leave a screen is trapped in it, and "finish or lose
       your progress" is exactly the coercion this product refuses. */
    const onLeave = vi.fn();
    runner({ onLeave });
    await start();

    await userEvent.click(ui().getByRole('button', { name: /stop for now/i }));
    expect(onLeave).toHaveBeenCalled();
  });

  it('never warns about losing progress on the way out', async () => {
    runner();
    await start();

    const text = document.querySelector('main')?.textContent ?? '';
    expect(text).not.toMatch(/lose your progress|you will lose|are you sure you want to quit/i);
  });
});

describe('finishing', () => {
  async function finish(correct: boolean) {
    runner();
    await start();

    await userEvent.click(ui().getByRole('button', { name: correct ? 'Good morning' : 'Good afternoon' }));
    await userEvent.click(ui().getByRole('button', { name: 'Next' }));
    await userEvent.click(ui().getByRole('button', { name: correct ? 'Good afternoon' : 'My name is Ravi' }));
    await userEvent.click(ui().getByRole('button', { name: 'Next' }));
    await userEvent.click(ui().getByRole('button', { name: /i said it/i }));
    await userEvent.click(ui().getByRole('button', { name: 'Next' }));
  }

  it('celebrates at the end of the level, not after every mission', async () => {
    /* Celebrating every correct answer devalues the currency and lengthens the
       session by about 40%. */
    runner();
    await start();
    await userEvent.click(ui().getByRole('button', { name: 'Good morning' }));

    expect(ui().queryByText(/level finished/i)).not.toBeInTheDocument();
  });

  it('shows the celebration once the last mission is done', async () => {
    await finish(true);
    expect(await ui().findByText(/level finished/i)).toBeInTheDocument();
  });

  it('awards three stars for a clean run', async () => {
    await finish(true);
    expect(await ui().findByRole('img', { name: '3 of 3 stars' })).toBeInTheDocument();
  });

  it('still awards a star for finishing after mistakes', async () => {
    await finish(false);
    const stars = await ui().findByRole('img', { name: /of 3 stars/ });
    expect(stars.getAttribute('aria-label')).not.toBe('0 of 3 stars');
  });
});

describe('the celebration', () => {
  function celebrate(level: 'full' | 'gentle' | 'still' = 'gentle', props = {}) {
    return shell(
      <Celebration
        starsEarned={2}
        xpEarned={40}
        level={level}
        onAgain={vi.fn()}
        onDone={vi.fn()}
        {...props}
      />,
    );
  }

  it('states every figure as text, not only as animation', async () => {
    celebrate();
    expect(ui().getByText('40 XP')).toBeInTheDocument();
    expect(ui().getByRole('img', { name: '2 of 3 stars' })).toBeInTheDocument();
  });

  it('announces once, as one complete sentence', async () => {
    /* The obvious implementation fires a live-region update per element, which
       a screen reader reads as three interruptions with the last two cutting
       off the first. */
    celebrate();

    await waitFor(
      () => {
        const live = document.querySelector('[aria-live="polite"]')?.textContent ?? '';
        expect(live).toContain('Level finished.');
        expect(live).toContain('2 of 3 stars.');
        expect(live).toContain('40 XP.');
      },
      { timeout: 2000 },
    );
  });

  it('gives "done for today" the same weight as "one more"', async () => {
    /* A product for people with fatigue conditions that makes stopping feel
       like quitting is a product that punishes fatigue. */
    celebrate();

    const again = ui().getByRole('button', { name: /one more/i });
    const done = ui().getByRole('button', { name: /done for today/i });

    expect(again.tagName).toBe(done.tagName);
    expect(done).toBeEnabled();
  });

  it('emits no particles below the Full motion level', async () => {
    celebrate('gentle', { starsEarned: 3 });
    expect(screen.queryByTestId('celebration-particles')).not.toBeInTheDocument();
  });

  it('caps a Full-level burst at 24 particles', async () => {
    /* Vestibular disorders are common and under-declared. Bounded, single
       emission, no loop (ADR-0010). */
    celebrate('full', { starsEarned: 3 });

    const burst = screen.getByTestId('celebration-particles');
    expect(burst.children.length).toBeLessThanOrEqual(24);
  });

  it('says the same things with all motion removed', async () => {
    /* The rule that makes motion safe: animation may only emphasise something
       already true in the DOM. */
    celebrate('still');

    expect(ui().getByText('40 XP')).toBeInTheDocument();
    expect(ui().getByRole('img', { name: '2 of 3 stars' })).toBeInTheDocument();
    expect(screen.queryByTestId('celebration-particles')).not.toBeInTheDocument();
  });

  it('mentions no streak at risk and nothing being lost', async () => {
    celebrate();
    const text = document.querySelector('main')?.textContent ?? '';
    expect(text).not.toMatch(/streak|at risk|don't lose|keep it up|you'll lose/i);
  });
});

describe('resolveCelebration', () => {
  it('defaults to Gentle, not Full', () => {
    expect(resolveCelebration(undefined, 'full')).toBe('gentle');
  });

  it('falls to Still when the OS asks for reduced motion', () => {
    expect(resolveCelebration(undefined, 'reduced')).toBe('still');
  });

  it('lets the learner override the OS in both directions', () => {
    /* The OS setting is a default, not a verdict. Somebody who set reduced
       motion months ago for a different app must be able to turn it back on. */
    expect(resolveCelebration('full', 'reduced')).toBe('full');
    expect(resolveCelebration('still', 'full')).toBe('still');
  });
});

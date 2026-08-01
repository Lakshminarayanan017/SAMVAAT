/**
 * The world map.
 *
 * The map is the screen a learner opens the app to see, which makes it the
 * screen where a regression is most expensive. What is asserted here is mostly
 * not "does it render" — it is that the game layer keeps its promises: nothing
 * locked, no colour-only meaning, and a screen reader hearing the same
 * information a sighted learner sees.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { WorldMap, type Journey } from '@/game/WorldMap';
import { blockingViolations, checkA11y, formatViolations } from '../a11y/axe';

function level(overrides: Partial<Journey['worlds'][0]['chapters'][0]['levels'][0]> = {}) {
  return {
    level_id: 'w1.c1.l1',
    title: 'First words',
    missions: ['recognise', 'produce'],
    status: 'recommended' as const,
    stars: 0,
    coverage: 0,
    retention: 0,
    effort: 4,
    caption: 'Start here.',
    ...overrides,
  };
}

function journey(overrides: Partial<Journey> = {}): Journey {
  return {
    headline: '3 stars so far.',
    total_stars: 3,
    max_stars: 150,
    next_level_id: 'w1.c1.l1',
    worlds: [
      {
        world_id: 'w01',
        order: 1,
        title: 'Finding Your Voice',
        subtitle: 'Saying hello, and saying who you are',
        easy_read_title: 'Saying hello',
        why: 'Every conversation starts here.',
        colour: 'dawn',
        icon: 'sunrise',
        flagship: false,
        is_current: true,
        caption: '1 of 4 levels finished. Keep going.',
        stars: 3,
        max_stars: 12,
        chapters: [
          {
            chapter_id: 'c1',
            title: 'Hello',
            sensitive: false,
            stars: 3,
            max_stars: 12,
            levels: [
              level({ level_id: 'w1.c1.l1', status: 'complete', stars: 3, caption: 'Finished.' }),
              level({ level_id: 'w1.c1.l2', title: 'Your name', status: 'recommended' }),
            ],
          },
        ],
      },
      {
        world_id: 'w10',
        order: 10,
        title: 'The Interview',
        subtitle: 'Everything you have learned',
        easy_read_title: 'Job interviews',
        why: 'The room where being qualified is not enough.',
        colour: 'gold',
        icon: 'door',
        flagship: true,
        is_current: false,
        caption: 'The room where being qualified is not enough.',
        stars: 0,
        max_stars: 18,
        chapters: [
          {
            chapter_id: 'c1',
            title: 'Your answers',
            sensitive: false,
            stars: 0,
            max_stars: 9,
            levels: [
              level({
                level_id: 'w10.c1.l1',
                title: 'Telling them about you',
                status: 'available_early',
                caption: 'Further on — you can still try it.',
              }),
            ],
          },
        ],
      },
    ],
    ...overrides,
  };
}

function renderMap(props: Partial<Parameters<typeof WorldMap>[0]> = {}) {
  const onOpenLevel = vi.fn();

  const result = render(
    <AnnouncerProvider>
      <WorldMap journey={journey()} onOpenLevel={onOpenLevel} {...props} />
    </AnnouncerProvider>,
  );

  return { ...result, onOpenLevel };
}

describe('nothing is ever locked', () => {
  it('an early level is a working button, not a disabled one', async () => {
    // A padlock on a product built for disabled people reads as "not for you".
    renderMap();

    await userEvent.click(screen.getByTestId('world-w10'));
    const tile = screen.getByTestId('level-w10.c1.l1');

    expect(tile).toBeEnabled();
    expect(tile).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('opens an early level when it is clicked', async () => {
    const { onOpenLevel } = renderMap();

    await userEvent.click(screen.getByTestId('world-w10'));
    await userEvent.click(screen.getByTestId('level-w10.c1.l1'));

    expect(onOpenLevel).toHaveBeenCalledWith('w10.c1.l1');
  });

  it('never uses the word locked on a world or a level', async () => {
    const { container } = renderMap();
    await userEvent.click(screen.getByTestId('world-w10'));

    // Scoped to the list. The map DOES say "nothing here is locked" once, as a
    // promise to the learner — that sentence is the point, not a violation.
    const list = container.querySelector('.world-list');
    const text = list?.textContent?.toLowerCase() ?? '';

    expect(text).not.toBe('');
    for (const word of ['locked', 'unlock', 'complete first', 'not available']) {
      expect(text).not.toContain(word);
    }
  });

  it('says so out loud that nothing is locked', () => {
    renderMap();
    expect(screen.getByText(/nothing here is locked/i)).toBeInTheDocument();
  });
});

describe('meaning never depends on colour', () => {
  it('marks the current world with a word as well as a border', () => {
    renderMap();
    const card = screen.getByTestId('world-w01');

    expect(within(card).getByText('Now')).toBeInTheDocument();
    expect(card).toHaveAttribute('data-current', 'true');
  });

  it('gives each world a distinct icon shape', () => {
    const { container } = renderMap();
    const paths = [...container.querySelectorAll('.world-card__icon path')].map((p) =>
      p.getAttribute('d'),
    );

    expect(new Set(paths).size).toBe(paths.length);
  });

  it('states the level status in text for a screen reader', async () => {
    renderMap();
    await userEvent.click(screen.getByTestId('world-w10'));

    // "Further on, and open" — an open door, not a warning.
    expect(screen.getByText(/further on, and open/i)).toBeInTheDocument();
  });
});

describe('the map is navigable', () => {
  it('opens the current world by default', () => {
    // A screen-reader user should not have to walk past fifty levels to reach
    // the one we are recommending.
    renderMap();

    expect(screen.getByTestId('world-w01')).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByTestId('world-w10')).toHaveAttribute('aria-expanded', 'false');
  });

  it('wires each world button to the panel it controls', () => {
    renderMap();
    const card = screen.getByTestId('world-w01');

    expect(card).toHaveAttribute('aria-controls', 'world-panel-w01');
    expect(document.getElementById('world-panel-w01')).toBeInTheDocument();
  });

  it('is reachable by keyboard alone', async () => {
    const { onOpenLevel } = renderMap();

    await userEvent.tab();
    await userEvent.tab();
    await userEvent.keyboard('{Enter}');

    expect(onOpenLevel).toHaveBeenCalled();
  });

  it('numbers the worlds for a screen reader', () => {
    renderMap();
    expect(screen.getByText(/world 1:/i)).toBeInTheDocument();
  });
});

describe('easy read', () => {
  it('uses the short titles and drops the subtitles', () => {
    renderMap({ easyRead: true });

    expect(screen.getByText('Saying hello')).toBeInTheDocument();
    expect(screen.queryByText('Saying hello, and saying who you are')).not.toBeInTheDocument();
  });
});

describe('sensitive chapters', () => {
  it('states the exit before a disclosure chapter is entered', () => {
    // A learner rehearsing disclosure is rehearsing something that can cost
    // them a job. The way out is offered before they start, not after.
    const withSensitive = journey();
    withSensitive.worlds[0].chapters[0].sensitive = true;

    render(
      <AnnouncerProvider>
        <WorldMap journey={withSensitive} onOpenLevel={vi.fn()} />
      </AnnouncerProvider>,
    );

    const notice = screen.getByTestId('sensitive-notice');
    expect(notice).toHaveTextContent(/stop any of these at any point/i);
    expect(notice).toHaveTextContent(/trainer/i);
  });
});

describe('reduced motion', () => {
  it('applies no animation delay when motion is reduced', () => {
    const { container } = renderMap({ motion: 'reduced' });

    for (const item of container.querySelectorAll('.world-list > li')) {
      expect((item as HTMLElement).style.animationDelay).toBe('0ms');
    }
  });
});

describe('accessibility', () => {
  it('has no critical or serious violations', async () => {
    const { container } = renderMap();
    const results = await checkA11y(container);

    expect(blockingViolations(results), formatViolations(results)).toEqual([]);
  });

  it('has none with a world expanded either', async () => {
    const { container } = renderMap();
    await userEvent.click(screen.getByTestId('world-w10'));

    const results = await checkA11y(container);
    expect(blockingViolations(results), formatViolations(results)).toEqual([]);
  });
});

/**
 * World identity and motion.
 *
 * Two properties, both of which are easy to lose in a redesign and impossible
 * to notice losing:
 *
 *   - the map works with no colour at all
 *   - every animation can be removed without removing meaning
 */
import { describe, expect, it } from 'vitest';

import {
  DURATION,
  EASING,
  celebrationDuration,
  keyframe,
  resolveMotion,
  stagger,
  transition,
} from '@/design-system/motion';
import {
  ICON_PATHS,
  NEUTRAL_PALETTE,
  WORLD_PALETTES,
  checkPalette,
  paletteFor,
} from '@/design-system/worlds';

describe('world palettes', () => {
  it('has a palette for every colour the curriculum names', async () => {
    const curriculum = await import('../../../../packages/content/dist/curriculum.json');
    const used = new Set(curriculum.default.worlds.map((world) => world.colour));

    for (const colour of used) {
      expect(WORLD_PALETTES[colour as string], `no palette for '${colour}'`).toBeDefined();
    }
  });

  it.each(Object.entries(WORLD_PALETTES))('%s clears AAA for text in both themes', (name, palette) => {
    const { lightText, darkText, passes } = checkPalette(palette);

    expect(
      passes,
      `${name}: light ${lightText.toFixed(2)}:1, dark ${darkText.toFixed(2)}:1, need 7:1`,
    ).toBe(true);
  });

  it('falls back to something plain rather than borrowing another world', () => {
    // A random pick would give an unknown world an identity that belongs to a
    // real one, which is worse than looking unfinished.
    expect(paletteFor('not-a-colour')).toBe(NEUTRAL_PALETTE);
  });

  it('gives every world a distinct icon', () => {
    const paths = Object.values(ICON_PATHS);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('has an icon for every world in the curriculum', async () => {
    const curriculum = await import('../../../../packages/content/dist/curriculum.json');

    for (const world of curriculum.default.worlds) {
      expect(ICON_PATHS[world.icon as keyof typeof ICON_PATHS], world.icon).toBeDefined();
    }
  });
});

describe('motion', () => {
  it('never runs anything longer than the switch-scan ceiling', () => {
    // A learner using switch scanning waits out every animation before the next
    // scan step is safe to read. A long celebration costs them real time on
    // every single item.
    for (const duration of Object.values(DURATION)) {
      expect(duration).toBeLessThanOrEqual(420);
    }
  });

  it('lets the learner override the OS setting in both directions', () => {
    // An OS setting is a default, not a verdict. Somebody who turned reduced
    // motion on for a different app must be able to turn it back on here.
    expect(resolveMotion(true)).toBe('reduced');
    expect(resolveMotion(false)).toBe('full');
  });

  it('keeps a cross-fade under reduced motion rather than cutting hard', () => {
    // A hard cut loses the signal that something changed, and that signal is
    // doing real work for a learner with a cognitive disability.
    const reduced = transition(['transform', 'opacity'], 'reduced');

    expect(reduced).toContain('opacity');
    expect(reduced).not.toContain('transform');
    expect(reduced).not.toBe('none');
  });

  it('drops movement through space under reduced motion', () => {
    // Scale, spin and translation are the vestibular triggers. Opacity is not.
    expect(keyframe('pop', 'reduced')).toBe('none');
    expect(keyframe('rise', 'reduced')).toBe('none');
    expect(keyframe('fade-in', 'reduced')).toBe('samvaad-fade-in');
  });

  it('keeps full motion intact', () => {
    expect(transition(['transform'], 'full')).toContain('transform');
    expect(keyframe('pop', 'full')).toBe('samvaad-pop');
  });

  it('removes stagger entirely under reduced motion', () => {
    expect(stagger(5, 'reduced')).toBe(0);
    expect(stagger(5, 'full')).toBeGreaterThan(0);
  });

  it('caps stagger so a long list does not crawl in', () => {
    // Fifty tiles at 40ms each would be two seconds of watching content the
    // learner already asked for arrive slowly.
    expect(stagger(200, 'full')).toBe(stagger(8, 'full'));
  });

  it('shortens celebrations rather than removing them under reduced motion', () => {
    expect(celebrationDuration('reduced')).toBeLessThan(celebrationDuration('full'));
    expect(celebrationDuration('reduced')).toBeGreaterThan(0);
  });

  it('uses easing curves that end, so announcements can be sequenced', () => {
    // A physics spring has no fixed duration, and an animation whose end nobody
    // can predict cannot be synchronised with a screen-reader announcement.
    for (const curve of Object.values(EASING)) {
      expect(curve).toMatch(/^cubic-bezier\(/);
    }
  });
});

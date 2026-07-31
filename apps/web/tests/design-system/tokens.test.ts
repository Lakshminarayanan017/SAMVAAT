/**
 * Contrast conformance for every theme.
 *
 * This is a gate, not documentation. A designer changing a hex value gets a
 * failing build rather than a low-vision learner getting an unreadable screen.
 *
 * Covers all four themes because contrast preference and colour scheme are
 * independent — it is entirely possible to break dark+standard while
 * light+standard still passes.
 */
import { describe, expect, it } from 'vitest';

import { CONTRAST_BAR, contrastRatio } from '@/design-system/contrast';
import { PALETTES, TARGET, TYPE, applyTheme } from '@/design-system/tokens';

const THEMES = [
  ['light', 'standard'],
  ['light', 'high_contrast'],
  ['dark', 'standard'],
  ['dark', 'high_contrast'],
] as const;

describe.each(THEMES)('palette: %s / %s', (scheme, contrast) => {
  const palette = PALETTES[scheme][contrast];

  // Body text is held to WCAG AAA (7:1), not AA (4.5:1). A low-vision learner
  // is persona P1, not an edge case.
  it.each([
    ['fg on bg', palette.fg, palette.bg],
    ['fg on surface', palette.fg, palette.surface],
    ['fgMuted on bg', palette.fgMuted, palette.bg],
    ['fgMuted on surface', palette.fgMuted, palette.surface],
    ['accent on bg', palette.accent, palette.bg],
    ['accentFg on accent', palette.accentFg, palette.accent],
  ])('%s clears the body-text bar', (_label, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(CONTRAST_BAR.bodyText);
  });

  it.each([
    ['focus on bg', palette.focus, palette.bg],
    ['focus on surface', palette.focus, palette.surface],
    ['border on bg', palette.border, palette.bg],
  ])('%s clears the UI-component bar', (_label, fg, bg) => {
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(CONTRAST_BAR.uiComponent);
  });
});

describe('contrastRatio', () => {
  it('returns the known extremes', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 1);
    expect(contrastRatio('#ffffff', '#ffffff')).toBeCloseTo(1, 5);
  });

  it('is symmetric', () => {
    expect(contrastRatio('#005a9c', '#ffffff')).toBeCloseTo(
      contrastRatio('#ffffff', '#005a9c'),
      10,
    );
  });

  it('accepts shorthand hex', () => {
    expect(contrastRatio('#000', '#fff')).toBeCloseTo(21, 1);
  });

  it('rejects malformed input rather than silently passing', () => {
    expect(() => contrastRatio('rebeccapurple', '#fff')).toThrow();
  });
});

describe('type scale', () => {
  it('has a base size of at least 18px, the Easy-Read floor', () => {
    // 1.125rem at the 16px browser default.
    expect(parseFloat(TYPE.size.base) * 16).toBeGreaterThanOrEqual(18);
  });

  it('never sets a line height below 1.5 for body copy', () => {
    expect(parseFloat(TYPE.lineHeight.base)).toBeGreaterThanOrEqual(1.5);
  });
});

describe('applyTheme', () => {
  it('writes custom properties and theme attributes', () => {
    const element = document.createElement('div');
    applyTheme({ colourScheme: 'dark', contrastTheme: 'high_contrast' }, element);

    expect(element.style.getPropertyValue('--colour-bg')).toBe('#000000');
    expect(element.style.getPropertyValue('--colour-fg-muted')).toBe('#ffffff');
    expect(element.dataset.contrastTheme).toBe('high_contrast');
    expect(element.dataset.colourScheme).toBe('dark');
  });

  it('clamps target size into the accessible range', () => {
    const element = document.createElement('div');

    applyTheme({ colourScheme: 'light', contrastTheme: 'standard', targetSizePx: 10 }, element);
    expect(element.style.getPropertyValue('--target-min')).toBe(`${TARGET.min}px`);

    applyTheme({ colourScheme: 'light', contrastTheme: 'standard', targetSizePx: 500 }, element);
    expect(element.style.getPropertyValue('--target-min')).toBe(`${TARGET.max}px`);
  });

  it('exposes reduced motion as a scale factor animations multiply by', () => {
    const element = document.createElement('div');
    applyTheme(
      { colourScheme: 'light', contrastTheme: 'standard', motionReduced: true },
      element,
    );
    expect(element.style.getPropertyValue('--motion-scale')).toBe('0');
  });
});

/**
 * The semantic layer, contrast-verified.
 *
 * Every role, in all four themes, against the bar its role requires. This is the
 * test that makes §9.2 a guarantee rather than an intention: a colour added to
 * `semantic.ts` that cannot meet its bar fails here, at the point somebody adds
 * it, rather than in a low-vision learner's session.
 *
 * The pairs checked are the pairs that actually occur. Checking every colour
 * against every other colour would produce failures for combinations no
 * component ever renders, and a test with known-irrelevant failures is a test
 * people learn to ignore.
 */
import { describe, expect, it } from 'vitest';

import { CONTRAST_BAR, contrastRatio } from '@/design-system/contrast';
import { ELEVATION, RADIUS_SCALE, semanticTokens } from '@/design-system/semantic';
import type { ColourScheme, ContrastTheme } from '@/design-system/tokens';

const THEMES: { scheme: ColourScheme; contrast: ContrastTheme }[] = [
  { scheme: 'light', contrast: 'standard' },
  { scheme: 'light', contrast: 'high_contrast' },
  { scheme: 'dark', contrast: 'standard' },
  { scheme: 'dark', contrast: 'high_contrast' },
];

function name(scheme: ColourScheme, contrast: ContrastTheme) {
  return `${scheme}/${contrast}`;
}

describe.each(THEMES)('theme $scheme/$contrast', ({ scheme, contrast }) => {
  const t = semanticTokens(scheme, contrast);
  const label = name(scheme, contrast);

  describe('text is readable on every surface it can land on', () => {
    it.each([
      ['textPrimary', 'surfaceBase'],
      ['textPrimary', 'surfaceRaised'],
      ['textPrimary', 'surfaceSunken'],
      ['textSecondary', 'surfaceBase'],
      ['textSecondary', 'surfaceRaised'],
      ['textSecondary', 'surfaceSunken'],
    ] as const)('%s on %s clears AAA', (ink, surface) => {
      const ratio = contrastRatio(t[ink], t[surface]);
      expect(ratio, `${label}: ${ink} on ${surface} is ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
        CONTRAST_BAR.bodyText,
      );
    });

    it('textSecondary is held to the same bar as textPrimary', () => {
      /* "Muted" is a visual weight, not a licence to fail. Secondary text is
         where contrast quietly slips in most design systems, and it is the text
         a low-vision learner is most often trying to read — captions, hints,
         the reason a figure was withheld. */
      expect(contrastRatio(t.textSecondary, t.surfaceRaised)).toBeGreaterThanOrEqual(
        CONTRAST_BAR.bodyText,
      );
    });
  });

  describe('controls are readable in every state', () => {
    it.each(['interactiveRest', 'interactiveHover', 'interactivePress'] as const)(
      'text on %s clears AAA',
      (state) => {
        const ratio = contrastRatio(t.textOnInteractive, t[state]);
        expect(ratio, `${label}: ${state} is ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
          CONTRAST_BAR.bodyText,
        );
      },
    );

    it('a control is distinguishable from the page it sits on', () => {
      expect(contrastRatio(t.interactiveRest, t.surfaceBase)).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
    });

    it('a control is distinguishable from a card it sits on', () => {
      expect(contrastRatio(t.interactiveRest, t.surfaceRaised)).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
    });
  });

  describe('status inks', () => {
    it.each(['successInk', 'attentionInk'] as const)('%s is readable as text', (ink) => {
      /* These are text-weight inks, not decorative fills. A "success green"
         that only works as a 4px bar is a colour that cannot say what happened
         to somebody who cannot see the bar. */
      expect(contrastRatio(t[ink], t.surfaceRaised)).toBeGreaterThanOrEqual(CONTRAST_BAR.bodyText);
      expect(contrastRatio(t[ink], t.surfaceBase)).toBeGreaterThanOrEqual(CONTRAST_BAR.bodyText);
    });

    it('success and attention are not the same colour', () => {
      /* In the high-contrast themes both collapse to the foreground ink on
         purpose — colour is unavailable there and text carries everything. That
         is a deliberate collapse, so it is asserted rather than excluded. */
      if (contrast === 'high_contrast') {
        expect(t.successInk).toBe(t.attentionInk);
      } else {
        expect(t.successInk).not.toBe(t.attentionInk);
      }
    });
  });

  describe('borders and focus', () => {
    it('borderSubtle clears the non-text bar', () => {
      expect(contrastRatio(t.borderSubtle, t.surfaceBase)).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
    });

    it('borderStrong clears the non-text bar on a raised surface', () => {
      expect(contrastRatio(t.borderStrong, t.surfaceRaised)).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
    });

    it('the focus ring is visible on every surface it can land on', () => {
      for (const surface of [t.surfaceBase, t.surfaceRaised, t.surfaceSunken] as const) {
        expect(contrastRatio(t.focusRing, surface)).toBeGreaterThanOrEqual(
          CONTRAST_BAR.uiComponent,
        );
      }
    });

    it('the two-tone ring is visible on a primary control', () => {
      /* Checked as the two boundaries the learner actually sees, because the
         single-colour version of this assertion fails in every theme: focus
         and accent are 1.31:1 in light/standard and IDENTICAL in both dark
         themes. A ring drawn straight onto a primary button would be invisible
         on the one control a learner is most likely to be tabbing to.
         `focusRingShadow` separates them with a surface-coloured inner ring. */
      const controlToInner = contrastRatio(t.interactiveRest, t.surfaceRaised);
      const innerToOuter = contrastRatio(t.surfaceRaised, t.focusRing);

      expect(controlToInner, `${label}: control vs inner ring`).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
      expect(innerToOuter, `${label}: inner ring vs outer ring`).toBeGreaterThanOrEqual(
        CONTRAST_BAR.uiComponent,
      );
    });

    it('a single-tone ring would NOT have been sufficient', () => {
      /* Pins the reason the two-tone ring exists. If a future palette change
         ever makes focus and accent genuinely distinguishable, this fails and
         somebody gets to decide deliberately whether to simplify — rather than
         the two-tone ring surviving forever as unexplained complexity. */
      expect(contrastRatio(t.focusRing, t.interactiveRest)).toBeLessThan(
        CONTRAST_BAR.uiComponent,
      );
    });
  });
});

describe('high contrast means what it says', () => {
  it('separates surfaces with borders rather than fills', () => {
    /* bg and surface are identical by design in these themes. A third invented
       shade would put back the low-contrast fill the theme exists to remove. */
    for (const scheme of ['light', 'dark'] as const) {
      const t = semanticTokens(scheme, 'high_contrast');
      expect(t.surfaceBase).toBe(t.surfaceRaised);
      expect(t.surfaceSunken).toBe(t.surfaceBase);
      expect(contrastRatio(t.borderStrong, t.surfaceRaised)).toBeGreaterThanOrEqual(7);
    }
  });

  it('does not soften secondary text', () => {
    for (const scheme of ['light', 'dark'] as const) {
      const t = semanticTokens(scheme, 'high_contrast');
      expect(t.textSecondary).toBe(t.textPrimary);
    }
  });
});

describe('elevation', () => {
  it('never relies on shadow alone', () => {
    /* Shadow vanishes in forced-colours mode and in both high-contrast themes.
       A learner using either would lose every card boundary on screen at once,
       so border weight carries elevation and shadow only reinforces it. */
    for (const [level, value] of Object.entries(ELEVATION)) {
      expect(value.border, `${level} has no border`).not.toBe('0');
      expect(parseFloat(value.border), `${level} border is not positive`).toBeGreaterThan(0);
    }
  });

  it('increases border weight as it rises', () => {
    expect(parseFloat(ELEVATION.overlay.border)).toBeGreaterThanOrEqual(
      parseFloat(ELEVATION.flat.border),
    );
  });
});

describe('radius', () => {
  it('offers a full round for pills and avatars', () => {
    expect(RADIUS_SCALE.full).toBe('999px');
  });

  it('ascends', () => {
    const px = (v: string) => parseFloat(v);
    expect(px(RADIUS_SCALE.sm)).toBeLessThan(px(RADIUS_SCALE.md));
    expect(px(RADIUS_SCALE.md)).toBeLessThan(px(RADIUS_SCALE.lg));
    expect(px(RADIUS_SCALE.lg)).toBeLessThan(px(RADIUS_SCALE.xl));
  });
});

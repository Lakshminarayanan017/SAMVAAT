/**
 * The v2 palette, contrast-verified.
 *
 * This is the test that makes the design system a guarantee rather than an
 * intention: a colour added or changed that cannot meet its bar fails here, at
 * the moment somebody changes it, rather than in a low-vision learner's
 * session.
 *
 * Only the pairs that actually occur are checked. Checking every colour against
 * every other would produce failures for combinations no component renders, and
 * a test with known-irrelevant failures is a test people learn to ignore.
 */
import { describe, expect, it } from 'vitest';

import { contrastRatio } from '@/design-system/contrast';
import {
  ELEVATION,
  PALETTES,
  RADIUS,
  TYPE,
  WORLD_HUES,
  worldHue,
  type Contrast,
  type Scheme,
} from '@/design/tokens';

const AAA = 7;
const NON_TEXT = 3;

const THEMES: { scheme: Scheme; contrast: Contrast }[] = [
  { scheme: 'light', contrast: 'standard' },
  { scheme: 'light', contrast: 'high' },
  { scheme: 'dark', contrast: 'standard' },
  { scheme: 'dark', contrast: 'high' },
];

describe.each(THEMES)('theme $scheme/$contrast', ({ scheme, contrast }) => {
  const p = PALETTES[scheme][contrast];
  const label = `${scheme}/${contrast}`;

  const SURFACES = ['canvas', 'surface', 'sunken'] as const;

  it.each(SURFACES)('body ink clears AAA on %s', (surface) => {
    const ratio = contrastRatio(p.ink, p[surface]);
    expect(ratio, `${label}: ink on ${surface} is ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(AAA);
  });

  it.each(SURFACES)('secondary ink clears the SAME bar on %s', (surface) => {
    /* "Muted" is a visual weight, not a licence to fail. Secondary text is
       where contrast quietly slips in most design systems, and it is the text
       a low-vision learner is most often trying to read — hints, captions, the
       reason a figure was withheld. */
    const ratio = contrastRatio(p.inkSoft, p[surface]);
    expect(
      ratio,
      `${label}: inkSoft on ${surface} is ${ratio.toFixed(2)}`,
    ).toBeGreaterThanOrEqual(AAA);
  });

  it.each(SURFACES)('the brand colour is readable as text on %s', (surface) => {
    const ratio = contrastRatio(p.brand, p[surface]);
    expect(ratio, `${label}: brand on ${surface}`).toBeGreaterThanOrEqual(AAA);
  });

  it.each(['brand', 'brandHover', 'brandPress'] as const)(
    'text on %s clears AAA',
    (state) => {
      const ratio = contrastRatio(p.onBrand, p[state]);
      expect(ratio, `${label}: onBrand over ${state}`).toBeGreaterThanOrEqual(AAA);
    },
  );

  it.each(SURFACES)('status inks are readable as text on %s', (surface) => {
    /* These are text-weight inks, not decorative fills. A success colour that
       only works as a 4px bar cannot say what happened to somebody who cannot
       see the bar. */
    for (const ink of ['good', 'attn', 'info'] as const) {
      const ratio = contrastRatio(p[ink], p[surface]);
      expect(ratio, `${label}: ${ink} on ${surface}`).toBeGreaterThanOrEqual(AAA);
    }
  });

  it('status washes carry their own ink', () => {
    expect(contrastRatio(p.good, p.goodWash)).toBeGreaterThanOrEqual(AAA);
    expect(contrastRatio(p.attn, p.attnWash)).toBeGreaterThanOrEqual(AAA);
  });

  it('the focus ring is visible on every surface it can land on', () => {
    for (const surface of ['canvas', 'surface', 'sunken'] as const) {
      expect(
        contrastRatio(p.focus, p[surface]),
        `${label}: focus on ${surface}`,
      ).toBeGreaterThanOrEqual(NON_TEXT);
    }
  });

  it('the two-tone ring is visible on a brand-filled button', () => {
    /* Checked as the two boundaries a learner actually sees. The single-colour
       version of this assertion fails in every theme — v2 focus ochre against
       the indigo brand is 1.37:1 — because both colours are mid-dark by
       necessity, each having to clear 7:1 against a near-white canvas.
       `focusRing()` separates them with a surface-coloured inner band. */
    expect(
      contrastRatio(p.brand, p.surface),
      `${label}: control vs inner band`,
    ).toBeGreaterThanOrEqual(NON_TEXT);
    expect(
      contrastRatio(p.surface, p.focus),
      `${label}: inner band vs outer band`,
    ).toBeGreaterThanOrEqual(NON_TEXT);
  });

  it('a single-tone ring would NOT have been sufficient', () => {
    /* Pins the reason the ring is two-tone. If a future palette ever makes a
       single ring viable, this fails and somebody decides deliberately to
       simplify — rather than the two-tone ring surviving forever as unexplained
       complexity. */
    expect(contrastRatio(p.focus, p.brand)).toBeLessThan(NON_TEXT);
  });

  it('hairlines clear the non-text bar', () => {
    expect(contrastRatio(p.line, p.canvas)).toBeGreaterThanOrEqual(NON_TEXT);
    expect(contrastRatio(p.lineStrong, p.surface)).toBeGreaterThanOrEqual(NON_TEXT);
  });
});

describe('high contrast means what it says', () => {
  it.each(['light', 'dark'] as const)('%s separates by border, not by fill', (scheme) => {
    const p = PALETTES[scheme].high;
    expect(p.canvas).toBe(p.surface);
    expect(p.sunken).toBe(p.canvas);
    expect(contrastRatio(p.lineStrong, p.surface)).toBeGreaterThanOrEqual(AAA);
  });

  it.each(['light', 'dark'] as const)('%s does not soften secondary text', (scheme) => {
    const p = PALETTES[scheme].high;
    expect(p.inkSoft).toBe(p.ink);
  });

  it.each(['light', 'dark'] as const)('%s collapses status colour into ink', (scheme) => {
    /* Colour is unavailable in these themes, so text carries everything. The
       collapse is deliberate, so it is asserted rather than excluded. */
    const p = PALETTES[scheme].high;
    expect(p.good).toBe(p.ink);
    expect(p.attn).toBe(p.ink);
  });
});

describe('world hues', () => {
  it('there are ten', () => {
    expect(WORLD_HUES).toHaveLength(10);
  });

  it('every hue carries readable text on the light canvas', () => {
    const canvas = PALETTES.light.standard.canvas;
    for (const [index, hue] of WORLD_HUES.entries()) {
      expect(
        contrastRatio(hue, canvas),
        `world ${index + 1} (${hue})`,
      ).toBeGreaterThanOrEqual(AAA);
    }
  });

  it('white text is readable on every hue', () => {
    for (const [index, hue] of WORLD_HUES.entries()) {
      expect(contrastRatio('#FFFFFF', hue), `world ${index + 1}`).toBeGreaterThanOrEqual(AAA);
    }
  });

  it('wraps rather than throwing past the tenth world', () => {
    expect(worldHue(10)).toBe(WORLD_HUES[0]);
    expect(worldHue(23)).toBe(WORLD_HUES[3]);
  });

  it('are never relied on alone for identity', () => {
    /* Ten hues that all clear 7:1 are necessarily crowded into a narrow
       luminance band, so any claim to tell them apart in greyscale would be
       false. This test pins the honest position: colour is the THIRD signal.
       Icon silhouette and the world's number and name carry identity, and
       `tests/game` asserts both are present on every world row. */
    const lum = (hex: string) => {
      const n = hex.replace('#', '');
      const ch = [0, 2, 4].map((i) => {
        const v = parseInt(n.slice(i, i + 2), 16) / 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * ch[0]! + 0.7152 * ch[1]! + 0.0722 * ch[2]!;
    };
    const spread = Math.max(...WORLD_HUES.map(lum)) - Math.min(...WORLD_HUES.map(lum));
    expect(spread).toBeLessThan(0.06);
  });
});

describe('elevation', () => {
  it('never relies on shadow alone', () => {
    /* Shadow vanishes entirely in forced-colours mode and both high-contrast
       themes. Without a border, every card boundary on screen would disappear
       at once for the learners who can least afford it. */
    for (const [level, value] of Object.entries(ELEVATION)) {
      expect(value.border, `${level} has no border`).toBeGreaterThan(0);
    }
  });

  it('gains border weight as it rises', () => {
    expect(ELEVATION.over.border).toBeGreaterThanOrEqual(ELEVATION.flat.border);
  });
});

describe('type scale', () => {
  it('body is at least 18px in both reading modes', () => {
    expect(parseFloat(TYPE.standard.body.size)).toBeGreaterThanOrEqual(1.125);
    expect(parseFloat(TYPE.easyRead.body.size)).toBeGreaterThanOrEqual(1.125);
  });

  it('captions grow under Easy-Read rather than shrinking', () => {
    /* Small supporting text is exactly what an Easy-Read reader most needs kept
       legible. "Captions are small" is a convention, not a requirement. */
    expect(parseFloat(TYPE.easyRead.caption.size)).toBeGreaterThan(
      parseFloat(TYPE.standard.caption.size),
    );
  });

  it('compresses the scale under Easy-Read rather than only enlarging it', () => {
    const spread = (t: typeof TYPE.standard) =>
      parseFloat(t.display.size) - parseFloat(t.caption.size);
    expect(spread(TYPE.easyRead)).toBeLessThan(spread(TYPE.standard));
  });

  it('never sets a line height below the WCAG 1.4.12 floor for body text', () => {
    for (const mode of [TYPE.standard, TYPE.easyRead]) {
      expect(parseFloat(mode.body.line)).toBeGreaterThanOrEqual(1.5);
      expect(parseFloat(mode.caption.line)).toBeGreaterThanOrEqual(1.5);
    }
  });
});

describe('radius', () => {
  it('ascends and offers a full round', () => {
    const px = (v: string) => parseFloat(v);
    expect(px(RADIUS[1])).toBeLessThan(px(RADIUS[2]));
    expect(px(RADIUS[2])).toBeLessThan(px(RADIUS[3]));
    expect(px(RADIUS[3])).toBeLessThan(px(RADIUS[4]));
    expect(RADIUS.full).toBe('999px');
  });
});

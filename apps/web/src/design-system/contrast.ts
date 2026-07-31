/**
 * WCAG relative luminance and contrast ratio.
 *
 * Lives in source rather than in a test helper because the token test, the
 * theme applier and any future colour picker must all agree on one
 * implementation. A second copy is a second answer.
 *
 * Reference: WCAG 2.2, Understanding Success Criterion 1.4.3.
 */

export type Rgb = { r: number; g: number; b: number };

export function parseHex(hex: string): Rgb {
  const clean = hex.replace('#', '');
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean;

  if (!/^[0-9a-fA-F]{6}$/.test(full)) {
    throw new Error(`not a hex colour: ${hex}`);
  }

  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  };
}

/** WCAG relative luminance of an sRGB colour. */
export function luminance(hex: string): number {
  const { r, g, b } = parseHex(hex);

  const channel = (value: number): number => {
    const s = value / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };

  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** Contrast ratio between two colours, from 1 (identical) to 21 (black on white). */
export function contrastRatio(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  const [lighter, darker] = la > lb ? [la, lb] : [lb, la];
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Our bars, deliberately above the WCAG minimums.
 *
 * WCAG 2.2 AA requires 4.5:1 for body text. We hold body text to AAA (7:1)
 * because a low-vision learner is a primary persona (P1), not an edge case.
 */
export const CONTRAST_BAR = {
  /** Body text against its background. WCAG AAA. */
  bodyText: 7,
  /** Large text (>=18.66px bold or >=24px). WCAG AAA for large text. */
  largeText: 4.5,
  /** Non-text UI: borders, focus rings, icons. WCAG 2.2 AA (1.4.11). */
  uiComponent: 3,
} as const;

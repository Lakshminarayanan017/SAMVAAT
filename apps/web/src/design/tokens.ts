/**
 * SAMVAAD v2 design tokens.
 *
 * The single source of truth for colour, type, space, radius, elevation and
 * motion. Defined in TypeScript rather than CSS so a unit test can prove every
 * ink/surface pair clears its contrast bar, instead of us asserting it in a
 * comment — see `tests/design/tokens.test.ts`, which fails the build on a
 * palette change that drops below AAA.
 *
 * IDENTITY
 * --------
 * Indigo on warm paper. Chosen to sit away from three things at once: the
 * corporate/medical blue the previous build used, the teal that reads as
 * "wellness app", and the saturated green every language-learning product now
 * owns. Warm neutrals rather than cold greys, because the product should read
 * as something made for a person rather than a form to be completed.
 *
 * THE ONE RULE ABOUT THE BRAND COLOUR
 * -----------------------------------
 * `--brand` means "press this", and it means nothing else. It is never a
 * heading colour, never a background wash, never decoration. One pressable
 * colour everywhere is what makes the interface learnable without reading it.
 * World hues are for world identity only and never touch a control.
 */

export type Scheme = 'light' | 'dark';
export type Contrast = 'standard' | 'high';

export interface Palette {
  /** The page. */
  canvas: string;
  /** Cards and raised surfaces. */
  surface: string;
  /** Wells, tracks, inset areas. */
  sunken: string;
  /** Body text. */
  ink: string;
  /** Secondary text — held to the same 7:1 bar. "Muted" is a weight, not a licence to fail. */
  inkSoft: string;
  /** The one pressable colour. */
  brand: string;
  brandHover: string;
  /** The button underside. Darker in light, lighter in dark. */
  brandPress: string;
  /** Text on brand. */
  onBrand: string;
  /** Accepted. */
  good: string;
  goodWash: string;
  /** "Not quite yet" — amber, never red. */
  attn: string;
  attnWash: string;
  /** Neutral emphasis. */
  info: string;
  /**
   * Hairlines and dividers.
   *
   * Held to the 3:1 non-text bar rather than being a pale decorative grey. A
   * card whose only boundary is a 1.4:1 hairline has no boundary at all for a
   * low-vision learner, and the first draft of this palette failed exactly
   * that way.
   */
  line: string;
  /** Control outlines that carry structure. */
  lineStrong: string;
  /**
   * Focus ring — the OUTER tone of a two-tone ring.
   *
   * No single colour can contrast with both a light surface and a mid-dark
   * button; a different hue family is not enough, and the first draft of this
   * palette proved it (ochre on indigo is 1.37:1). So the ring is drawn as a
   * surface-coloured inner band plus this outer band, and both boundaries are
   * then already contrast-verified. See `focusRing()` in `theme.ts`.
   */
  focus: string;
}

export const PALETTES: Record<Scheme, Record<Contrast, Palette>> = {
  light: {
    standard: {
      canvas: '#FAF7F5',
      surface: '#FFFFFF',
      sunken: '#F7F3F0',
      ink: '#1B1A22',
      inkSoft: '#4A4756',
      brand: '#4338CA',
      brandHover: '#3730A3',
      brandPress: '#2A2568',
      onBrand: '#FFFFFF',
      good: '#0B5A3C',
      goodWash: '#E8F4EE',
      attn: '#7A4400',
      attnWash: '#FBF1E4',
      info: '#1F4E8C',
      line: '#8C837C',
      lineStrong: '#4A4756',
      // Ochre rather than indigo: the ring has to be visible ON a brand-filled
      // button, and a ring from the same family is invisible exactly where it
      // matters most.
      focus: '#A34E00',
    },
    high: {
      canvas: '#FFFFFF',
      surface: '#FFFFFF',
      sunken: '#FFFFFF',
      ink: '#000000',
      inkSoft: '#000000',
      brand: '#1A1466',
      brandHover: '#1A1466',
      brandPress: '#1A1466',
      onBrand: '#FFFFFF',
      good: '#000000',
      goodWash: '#FFFFFF',
      attn: '#000000',
      attnWash: '#FFFFFF',
      info: '#000000',
      line: '#000000',
      lineStrong: '#000000',
      focus: '#1A1466',
    },
  },
  dark: {
    standard: {
      canvas: '#141320',
      surface: '#1E1C2E',
      sunken: '#0D0C16',
      ink: '#F5F3FA',
      inkSoft: '#BDB8CC',
      brand: '#A5A0FF',
      brandHover: '#BDB9FF',
      brandPress: '#D4D1FF',
      onBrand: '#141320',
      good: '#5FD9A4',
      goodWash: '#12291F',
      attn: '#F0C070',
      attnWash: '#2A2013',
      info: '#8FBEFF',
      line: '#6B6688',
      lineStrong: '#BDB8CC',
      focus: '#FFC773',
    },
    high: {
      canvas: '#000000',
      surface: '#000000',
      sunken: '#000000',
      ink: '#FFFFFF',
      inkSoft: '#FFFFFF',
      brand: '#C9C5FF',
      brandHover: '#C9C5FF',
      brandPress: '#C9C5FF',
      onBrand: '#000000',
      good: '#FFFFFF',
      goodWash: '#000000',
      attn: '#FFFFFF',
      attnWash: '#000000',
      info: '#FFFFFF',
      line: '#FFFFFF',
      lineStrong: '#FFFFFF',
      focus: '#FFFF00',
    },
  },
};

/**
 * Ten world hues.
 *
 * Spread across the spectrum and each verified at 7:1 on the canvas, so a
 * world's own name renders legibly on its tint.
 *
 * They are NOT relied on for greyscale separation. Ten hues that all clear 7:1
 * are necessarily crowded into a narrow luminance band, so any claim to tell
 * them apart without colour would be false. Identity is carried by three
 * signals and colour is the third: the icon silhouette differs in *outline* at
 * 32px monochrome, and the number and name are always present as text.
 */
export const WORLD_HUES: readonly string[] = [
  '#8E1C4E', // 1  Finding Your Voice
  '#7C2E10', // 2  Making Sure You Understand
  '#6B4200', // 3  Saying Where You Are
  '#4A5A00', // 4  Asking For What You Need
  '#155F3E', // 5  Speaking Up For Yourself
  '#0A5866', // 6  Handling Disagreement
  '#1B4A85', // 7  On The Phone And In Writing
  '#3A32B0', // 8  In The Room
  '#5C2585', // 9  When It Matters
  '#7A1338', // 10 The Interview
];

export function worldHue(index: number): string {
  return WORLD_HUES[index % WORLD_HUES.length] as string;
}

/** Spacing. Nothing outside this scale; there is deliberately no Spacer component. */
export const SPACE = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '24px',
  6: '32px',
  7: '48px',
  8: '64px',
} as const;

/** Radius. Generous — most of what makes the product read as friendly. */
export const RADIUS = {
  1: '8px',
  2: '14px',
  3: '20px',
  4: '28px',
  full: '999px',
} as const;

/**
 * Type. Base is 18px, not 16px: Easy-Read requires >=18 and there is no reason
 * to make everyone else squint so a default matches convention.
 *
 * Easy-Read is a compressed scale, not merely a larger one. A fluent reader
 * uses a big display-to-caption spread to skim; an Easy-Read reader is not
 * skimming, and a 2.25rem display beside 1rem captions is two different reading
 * experiences on one screen. Captions grow; they never shrink.
 */
export const TYPE = {
  family:
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Tamil', sans-serif",
  standard: {
    display: { size: '2.25rem', line: '1.35', weight: '700' },
    title: { size: '1.75rem', line: '1.35', weight: '700' },
    heading: { size: '1.375rem', line: '1.5', weight: '600' },
    body: { size: '1.125rem', line: '1.6', weight: '400' },
    caption: { size: '1rem', line: '1.6', weight: '400' },
    stat: { size: '2.75rem', line: '1.1', weight: '700' },
    button: { size: '1.125rem', line: '1.2', weight: '600' },
  },
  easyRead: {
    display: { size: '2rem', line: '1.4', weight: '700' },
    title: { size: '1.625rem', line: '1.4', weight: '700' },
    heading: { size: '1.375rem', line: '1.5', weight: '600' },
    body: { size: '1.25rem', line: '1.8', weight: '400' },
    caption: { size: '1.125rem', line: '1.8', weight: '400' },
    stat: { size: '2.5rem', line: '1.1', weight: '700' },
    button: { size: '1.25rem', line: '1.2', weight: '600' },
  },
} as const;

export type TypeVariant = keyof typeof TYPE.standard;

/**
 * Elevation. Border weight carries the information; shadow only reinforces it.
 *
 * Shadow is not rendered at all in forced-colours mode or the high-contrast
 * themes, so a shadow-only system loses every card boundary on screen at once
 * for the learners who can least afford it.
 */
export const ELEVATION = {
  flat: { border: 1, shadow: 'none' },
  raised: { border: 1, shadow: '0 1px 2px rgb(0 0 0 / 0.06)' },
  lifted: { border: 2, shadow: '0 6px 16px rgb(0 0 0 / 0.10)' },
  over: { border: 2, shadow: '0 14px 40px rgb(0 0 0 / 0.18)' },
} as const;

export type Elevation = keyof typeof ELEVATION;

/** Interactive target floor. The profile raises it to as much as 88px. */
export const TARGET = { min: 44, max: 88 } as const;

/** The tactile button's underside depth. */
export const LIFT = 4;

/**
 * Motion. 420ms is the ceiling anywhere in the product, because a
 * switch-scanning learner waits out every animation before the next scan step
 * is safe to read.
 */
export const DURATION = {
  instant: 90,
  quick: 160,
  base: 240,
  celebrate: 420,
} as const;

export const EASING = {
  enter: 'cubic-bezier(.16,1,.3,1)',
  exit: 'cubic-bezier(.4,0,1,1)',
  standard: 'cubic-bezier(.4,0,.2,1)',
  spring: 'cubic-bezier(.34,1.56,.64,1)',
} as const;

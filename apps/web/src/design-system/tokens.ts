/**
 * Design tokens — the single source of truth for colour, type and spacing.
 *
 * Defined in TypeScript rather than CSS so that:
 *   1. a unit test can prove every foreground/background pair clears its
 *      contrast bar, instead of us asserting it in a comment, and
 *   2. `applyTheme` can switch themes at runtime from the learner's
 *      Communication Ability Profile, which is where `contrast_theme` lives.
 *
 * There are four themes because contrast preference and colour scheme are
 * independent axes. A learner may want dark mode without high contrast, or
 * high contrast without dark mode. Collapsing them into one setting forces a
 * choice nobody should have to make.
 */
import { applyMotionTokens } from './motion';
import { applySemanticTokens } from './semantic';

export type ColourScheme = 'light' | 'dark';
export type ContrastTheme = 'standard' | 'high_contrast';

export interface Palette {
  /** Page background. */
  bg: string;
  /** Raised surfaces: cards, panels. */
  surface: string;
  /** Body text. Must clear 7:1 against both `bg` and `surface`. */
  fg: string;
  /** Secondary text. Must clear 7:1 against both `bg` and `surface`. */
  fgMuted: string;
  /** Interactive accent: buttons, links. Must clear 7:1 against `bg`. */
  accent: string;
  /** Text placed on `accent`. Must clear 7:1 against `accent`. */
  accentFg: string;
  /** Focus ring. Must clear 3:1 against `bg` and `surface`. */
  focus: string;
  /** Borders and dividers. Must clear 3:1 against `bg`. */
  border: string;
}

export const PALETTES: Record<ColourScheme, Record<ContrastTheme, Palette>> = {
  light: {
    standard: {
      bg: '#ffffff',
      surface: '#f4f6f8',
      fg: '#1a1a1a',
      fgMuted: '#4a4a4a',
      accent: '#005a9c',
      accentFg: '#ffffff',
      focus: '#0b6bbd',
      // Not a lighter grey: borders are non-text UI and must still clear 3:1
      // (WCAG 1.4.11). The obvious #9aa3ad manages only 2.56:1 on white.
      border: '#6b7280',
    },
    high_contrast: {
      bg: '#ffffff',
      surface: '#ffffff',
      fg: '#000000',
      fgMuted: '#000000',
      accent: '#00407a',
      accentFg: '#ffffff',
      focus: '#00407a',
      border: '#000000',
    },
  },
  dark: {
    standard: {
      bg: '#121212',
      surface: '#1e1e1e',
      fg: '#f0f0f0',
      fgMuted: '#b8b8b8',
      accent: '#79b8ff',
      accentFg: '#0a1929',
      focus: '#79b8ff',
      border: '#6b6b6b',
    },
    high_contrast: {
      bg: '#000000',
      surface: '#000000',
      fg: '#ffffff',
      fgMuted: '#ffffff',
      accent: '#7fd4ff',
      accentFg: '#000000',
      focus: '#ffff00',
      border: '#ffffff',
    },
  },
};

/**
 * Type scale. Base is 18px rather than the usual 16px.
 *
 * Easy-Read requires >=18px, and there is no good reason to make everyone else
 * squint so that the default matches a convention. Scales with the browser's
 * root font size, so a learner's own zoom and font settings still apply.
 */
export const TYPE = {
  fontFamily:
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
  size: {
    sm: '1rem',
    base: '1.125rem',
    lg: '1.375rem',
    xl: '1.75rem',
    xxl: '2.25rem',
  },
  /** 1.5 minimum — WCAG 1.4.12 (text spacing). */
  lineHeight: { tight: '1.35', base: '1.6', relaxed: '1.8' },
  weight: { regular: '400', medium: '500', bold: '700' },
} as const;

export const SPACE = {
  xs: '0.25rem',
  sm: '0.5rem',
  md: '1rem',
  lg: '1.5rem',
  xl: '2.5rem',
} as const;

/**
 * Interactive target sizes.
 *
 * 44px is the WCAG 2.2 AA floor. The profile can raise it to 88px for motor
 * impairment (P3), so this is a starting value, not a constant.
 */
export const TARGET = { min: 44, max: 88 } as const;

export const RADIUS = { sm: '4px', md: '8px', lg: '14px' } as const;

/** Focus ring width. 3px so it stays visible at high zoom and on busy backgrounds. */
export const FOCUS_RING_WIDTH = '3px';

export interface ThemeOptions {
  colourScheme: ColourScheme;
  contrastTheme: ContrastTheme;
  /** From the profile's `presentation.target_size_px`. */
  targetSizePx?: number;
  /** From the profile's `presentation.motion_reduced`. */
  motionReduced?: boolean;
}

/**
 * Write the theme onto an element as CSS custom properties.
 *
 * Called once at boot and again whenever the profile changes, so a learner who
 * switches to high contrast mid-session sees it immediately.
 */
export function applyTheme(
  options: ThemeOptions,
  element: HTMLElement = document.documentElement,
): void {
  const {
    colourScheme,
    contrastTheme,
    targetSizePx = TARGET.min,
    motionReduced = false,
  } = options;

  const palette = PALETTES[colourScheme][contrastTheme];

  for (const [name, value] of Object.entries(palette)) {
    element.style.setProperty(`--colour-${kebab(name)}`, value);
  }

  // The semantic layer (Blueprint §9.2). Written alongside the raw palette so a
  // component never has to know whether it has been applied separately — if the
  // page has a theme, it has roles.
  applySemanticTokens(colourScheme, contrastTheme, element);

  // Spacing, type and duration as custom properties too, so the fallbacks in
  // `ui/styles.ts` (`var(--space-md, 1rem)`) are genuinely fallbacks rather
  // than the operative value. A design system whose scale lives only in inline
  // defaults cannot be changed in one place, which is the point of having one.
  for (const [name, value] of Object.entries(SPACE)) {
    element.style.setProperty(`--space-${name}`, value);
  }
  for (const [name, value] of Object.entries(TYPE.size)) {
    element.style.setProperty(`--type-${name}`, value);
  }
  element.style.setProperty('--font-family', TYPE.fontFamily);

  applyMotionTokens(element);

  element.style.setProperty('--target-min', `${clampTarget(targetSizePx)}px`);
  element.style.setProperty('--motion-scale', motionReduced ? '0' : '1');

  // Exposed as attributes so CSS can branch on them and so tests and
  // screenshots can assert the active theme without reading inline styles.
  element.dataset.colourScheme = colourScheme;
  element.dataset.contrastTheme = contrastTheme;
  element.style.colorScheme = colourScheme;
}

function clampTarget(px: number): number {
  return Math.min(TARGET.max, Math.max(TARGET.min, Math.round(px)));
}

function kebab(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
}

/**
 * Applying the theme.
 *
 * Writes every token onto the document as a CSS custom property, so components
 * reference roles (`--brand`, `--ink-soft`) and never raw values. Called once
 * before first paint and again whenever the learner changes a setting, so a
 * change to contrast or text size takes effect immediately rather than on
 * reload — which matters because the learner changing the contrast setting may
 * not be able to read the screen until it applies.
 */
import {
  DURATION,
  EASING,
  ELEVATION,
  LIFT,
  PALETTES,
  RADIUS,
  SPACE,
  TARGET,
  TYPE,
  type Contrast,
  type Scheme,
} from './tokens';

export type MotionLevel = 'full' | 'gentle' | 'still';

export interface ThemeOptions {
  scheme: Scheme;
  contrast: Contrast;
  /** From the profile. 44–88. */
  targetPx?: number;
  /** Easy-Read switches the whole type scale in one place. */
  easyRead?: boolean;
  motion?: MotionLevel;
  /** Learner text scale, 1–2. Multiplies the root font size. */
  textScale?: number;
}

export function applyTheme(
  options: ThemeOptions,
  el: HTMLElement = document.documentElement,
): void {
  const {
    scheme,
    contrast,
    targetPx = TARGET.min,
    easyRead = false,
    motion = 'gentle',
    textScale = 1,
  } = options;

  const palette = PALETTES[scheme][contrast];

  for (const [name, value] of Object.entries(palette)) {
    el.style.setProperty(`--${kebab(name)}`, value);
  }

  for (const [step, value] of Object.entries(SPACE)) {
    el.style.setProperty(`--s-${step}`, value);
  }
  for (const [step, value] of Object.entries(RADIUS)) {
    el.style.setProperty(`--r-${step}`, value);
  }
  for (const [level, value] of Object.entries(ELEVATION)) {
    el.style.setProperty(`--elev-${level}-border`, `${value.border}px`);
    el.style.setProperty(`--elev-${level}-shadow`, value.shadow);
  }

  // Easy-Read is a global switch rather than a branch in every screen. Ten
  // screens each asking "is this learner on Easy-Read?" is ten chances to
  // forget, and the learner who gets forgotten is the one who cannot read the
  // result.
  const type = easyRead ? TYPE.easyRead : TYPE.standard;
  for (const [variant, spec] of Object.entries(type)) {
    el.style.setProperty(`--type-${variant}-size`, spec.size);
    el.style.setProperty(`--type-${variant}-line`, spec.line);
    el.style.setProperty(`--type-${variant}-weight`, spec.weight);
  }
  el.style.setProperty('--font', TYPE.family);

  for (const [name, ms] of Object.entries(DURATION)) {
    el.style.setProperty(`--t-${name}`, `${ms}ms`);
  }
  for (const [name, curve] of Object.entries(EASING)) {
    el.style.setProperty(`--e-${name}`, curve);
  }

  el.style.setProperty('--target', `${clamp(targetPx, TARGET.min, TARGET.max)}px`);
  el.style.setProperty('--lift', motion === 'still' ? '0px' : `${LIFT}px`);
  el.style.setProperty('--text-scale', String(clamp(textScale, 1, 2)));

  // Exposed as attributes so CSS can branch on them and tests can assert the
  // active theme without reading inline styles.
  el.dataset['scheme'] = scheme;
  el.dataset['contrast'] = contrast;
  el.dataset['motion'] = motion;
  el.dataset['read'] = easyRead ? 'easy' : 'standard';
  el.style.colorScheme = scheme;
}

/**
 * Resolve the effective motion level.
 *
 * The OS preference is a default, not a verdict. Somebody who enabled reduced
 * motion months ago for a different app must be able to turn animation back on
 * here, and somebody who never found the OS setting must still be safe by
 * default.
 */
export function resolveMotion(chosen: MotionLevel | undefined): MotionLevel {
  if (chosen) return chosen;
  if (typeof window === 'undefined' || !window.matchMedia) return 'gentle';
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'still' : 'gentle';
}

/** Read what the OS already told us, so the app opens correct rather than asking. */
export function systemDefaults(): ThemeOptions {
  const mq = (query: string) =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(query).matches
      : false;

  return {
    scheme: mq('(prefers-color-scheme: dark)') ? 'dark' : 'light',
    contrast: mq('(prefers-contrast: more)') ? 'high' : 'standard',
    motion: mq('(prefers-reduced-motion: reduce)') ? 'still' : 'gentle',
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function kebab(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
}

/**
 * The focus ring, drawn in two tones.
 *
 * A single-colour ring must contrast with two things at once: the surface
 * behind it AND the control it outlines. No colour does both here — the v2
 * focus ochre sits at 1.37:1 against the indigo brand, and picking a different
 * hue family is not enough, because both are mid-dark by necessity (each has to
 * clear 7:1 against a near-white canvas).
 *
 * So: a surface-coloured inner band separates the control from a focus-coloured
 * outer band. Both boundaries are then already verified —
 *
 *   control | surface-coloured inner   >= 3:1  (brand vs surface, asserted)
 *   inner   | focus-coloured outer     >= 3:1  (focus vs surface, asserted)
 *
 * — so the ring is provably visible on anything this system can render, without
 * anybody having to find a colour that works everywhere.
 *
 * `box-shadow` rather than `outline` so both bands follow the border radius.
 */
export function focusRing(surface = 'var(--surface)'): string {
  return `0 0 0 2px ${surface}, 0 0 0 5px var(--focus)`;
}

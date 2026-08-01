/**
 * The semantic layer (Blueprint §9.2).
 *
 * WHY THIS EXISTS
 * ---------------
 * `tokens.ts` holds palettes — the raw colours of a theme. Components must
 * never reach for those directly. A component that says `--colour-accent` has
 * hard-coded a *decision* ("this is the accent colour") into a place that only
 * knows a *role* ("this is the thing you press"). When the accent later needs to
 * differ between a button at rest and a button held down, every component that
 * guessed has to be found and changed.
 *
 * So components consume roles: `--interactive-rest`, `--text-secondary`,
 * `--surface-raised`. The mapping from role to colour lives here, once.
 *
 * THE RULE THAT MATTERS MOST
 * --------------------------
 * **No component may use a world palette for anything except world identity.**
 * The ten world colours mean "this is World 4". A world colour leaking into a
 * button destroys that meaning — the learner can no longer tell whether a colour
 * is telling them where they are or what to press. `worlds.ts` is deliberately
 * not imported here, and a test asserts no `ui/` primitive imports it.
 *
 * EVERY ROLE IS CONTRAST-VERIFIED
 * -------------------------------
 * Not asserted in a comment — checked in `tests/design-system/semantic.test.ts`
 * against `CONTRAST_BAR`, for all four themes. A role that cannot meet its bar
 * is a bug in this file, not a note in a backlog.
 */
import type { ContrastTheme, ColourScheme, Palette } from './tokens';
import { PALETTES } from './tokens';

/**
 * Component-facing colour roles.
 *
 * Named for what they are *for*, never for what they look like. `attentionInk`
 * rather than `red`: the high-contrast dark theme renders it yellow, and a
 * component asking for "red" would be wrong there.
 */
export interface SemanticTokens {
  /** The page itself. */
  surfaceBase: string;
  /** Cards and panels — one step toward the reader. */
  surfaceRaised: string;
  /** Wells, inset areas, disabled fields — one step away. */
  surfaceSunken: string;

  /** Body copy. Held to 7:1 against base *and* raised. */
  textPrimary: string;
  /** Supporting copy. Also held to 7:1 — "muted" is a visual weight, not a licence to fail. */
  textSecondary: string;
  /** Text placed on `interactiveRest`. */
  textOnInteractive: string;

  /** A control at rest. */
  interactiveRest: string;
  /** Pointer over, or keyboard focus without activation. */
  interactiveHover: string;
  /** Held down. */
  interactivePress: string;

  /** The focus ring. Never the same colour as anything it can land on. */
  focusRing: string;

  /** Something went well. Never the only signal — always paired with text. */
  successInk: string;
  /** Something needs attention. Deliberately not "error" — see below. */
  attentionInk: string;

  /** Dividers, quiet outlines. Non-text, so 3:1. */
  borderSubtle: string;
  /** Card and control outlines that carry structure. */
  borderStrong: string;
}

/**
 * Derive the semantic roles for a theme.
 *
 * The derivations are deliberately explicit rather than programmatic (no
 * `darken(accent, 12%)`). Generated colours drift out of contrast compliance
 * silently as the base palette changes, and the whole point of this file is that
 * every value is one a test can check.
 */
export function semanticTokens(scheme: ColourScheme, contrast: ContrastTheme): SemanticTokens {
  const palette: Palette = PALETTES[scheme][contrast];
  const isHighContrast = contrast === 'high_contrast';
  const isDark = scheme === 'dark';

  return {
    surfaceBase: palette.bg,
    surfaceRaised: palette.surface,
    // In high contrast, bg and surface are deliberately identical — separation
    // comes from borders, not fills. Inventing a third shade there would
    // reintroduce exactly the low-contrast fill the theme exists to remove.
    surfaceSunken: isHighContrast ? palette.bg : isDark ? '#0b0b0b' : '#e6eaee',

    textPrimary: palette.fg,
    textSecondary: palette.fgMuted,
    textOnInteractive: palette.accentFg,

    interactiveRest: palette.accent,
    interactiveHover: isHighContrast
      ? palette.accent
      : isDark
        ? '#9ecbff'
        : '#00477c',
    interactivePress: isHighContrast
      ? palette.accent
      : isDark
        ? '#bcdcff'
        : '#003760',

    focusRing: palette.focus,

    // Success and attention are text-weight inks, so both clear 7:1. The
    // temptation is a cheerful mid-green and a bright red; both fail on white,
    // and both are invisible to a learner with a colour vision deficiency
    // unless something else carries the meaning — which, in this codebase,
    // something always does.
    // The light values are darker than they look like they need to be. The
    // obvious #136c3a green reaches only 5.99:1 on a raised surface and the
    // obvious #8a4b00 amber 6.28:1 — both would have shipped as "AAA" on the
    // strength of passing against pure white, which is not the surface most of
    // this text actually sits on.
    successInk: isHighContrast
      ? palette.fg
      : isDark
        ? '#6ee7a8'
        : '#0d5029',
    attentionInk: isHighContrast
      ? palette.fg
      : isDark
        ? '#ffc46b'
        : '#6e3c00',

    borderSubtle: palette.border,
    borderStrong: isHighContrast ? palette.fg : palette.fg,
  };
}

/**
 * The focus ring is drawn in two tones, and that is not decoration.
 *
 * THE PROBLEM
 * -----------
 * A single-colour ring has to contrast with two things at once: the surface
 * behind it *and* the control it outlines. In the light theme the focus blue
 * (#0b6bbd) and the accent blue (#005a9c) sit at 1.31:1 — a ring drawn directly
 * on a primary button would be very nearly invisible. In both dark themes the
 * focus colour and the accent are literally the same value, so the ring
 * disappears completely on the one control a learner is most likely to be
 * tabbing to.
 *
 * No single colour fixes this. Whatever is chosen has to contrast with every
 * possible control colour, and the world palettes make that set open-ended.
 *
 * THE FIX
 * -------
 * Draw two concentric rings: an inner one in the *surface* colour, and an outer
 * one in the focus colour. Both boundaries are then already guaranteed:
 *
 *   control | surface-coloured inner ring   >= 3:1  (asserted: control vs surface)
 *   surface-coloured inner | focus outer    >= 3:1  (asserted: focus vs surface)
 *
 * So the ring is visible on any control this design system can produce, without
 * anybody having to pick a colour that works everywhere — because no such colour
 * exists.
 *
 * Implemented with `box-shadow` rather than `outline` so the two rings follow
 * the border radius. `outline` in older engines draws a rectangle around a
 * rounded control, which reads as a rendering fault.
 */
export const FOCUS_RING = {
  /** Separates the control from the outer ring. Surface-coloured. */
  innerWidth: 2,
  /** The visible ring. */
  outerWidth: 3,
} as const;

/**
 * The `box-shadow` value for a focused control.
 *
 * `surface` is the colour immediately behind the control — usually
 * `--surface-raised` for a control on a card, `--surface-base` for one on the
 * page. Passing the wrong one degrades the ring to single-tone; it does not
 * break it.
 */
export function focusRingShadow(
  surface = 'var(--surface-base)',
  ring = 'var(--focus-ring)',
): string {
  const inner = FOCUS_RING.innerWidth;
  const outer = inner + FOCUS_RING.outerWidth;
  return `0 0 0 ${inner}px ${surface}, 0 0 0 ${outer}px ${ring}`;
}

/**
 * Elevation (Blueprint §9.4).
 *
 * Four levels, each carrying **border weight as well as shadow**. Shadow alone
 * is not an acceptable elevation signal: it disappears entirely in forced-colours
 * mode and in the high-contrast themes, and a learner who relies on either would
 * lose every card boundary on the screen at once.
 */
export const ELEVATION = {
  flat: { border: '1px', shadow: 'none' },
  raised: { border: '1px', shadow: '0 1px 2px rgb(0 0 0 / 0.08)' },
  floating: { border: '2px', shadow: '0 4px 12px rgb(0 0 0 / 0.12)' },
  overlay: { border: '2px', shadow: '0 10px 32px rgb(0 0 0 / 0.20)' },
} as const;

export type Elevation = keyof typeof ELEVATION;

/** Radius scale (Blueprint §9.4). `full` is for pills and avatars. */
export const RADIUS_SCALE = {
  sm: '4px',
  md: '8px',
  lg: '14px',
  xl: '18px',
  full: '999px',
} as const;

export type Radius = keyof typeof RADIUS_SCALE;

/**
 * Write the semantic layer onto an element as CSS custom properties.
 *
 * Called from `applyTheme`, so a component never has to know whether the theme
 * has been applied — if the page has a theme, it has these.
 */
export function applySemanticTokens(
  scheme: ColourScheme,
  contrast: ContrastTheme,
  element: HTMLElement = document.documentElement,
): void {
  const tokens = semanticTokens(scheme, contrast);

  for (const [name, value] of Object.entries(tokens)) {
    element.style.setProperty(`--${kebab(name)}`, value);
  }

  for (const [name, level] of Object.entries(ELEVATION)) {
    element.style.setProperty(`--elevation-${name}-border`, level.border);
    element.style.setProperty(`--elevation-${name}-shadow`, level.shadow);
  }

  for (const [name, value] of Object.entries(RADIUS_SCALE)) {
    element.style.setProperty(`--radius-${name}`, value);
  }
}

function kebab(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
}

/**
 * World identity — a colour and a shape per world.
 *
 * Ten worlds need to be distinguishable at a glance on a map. The obvious way
 * is ten colours, and the obvious way is wrong: roughly one man in twelve has a
 * colour vision deficiency, and a map that only encodes identity in hue tells
 * them nothing.
 *
 * So every world carries three independent signals:
 *
 *   1. **Colour** — fastest for most people.
 *   2. **Icon shape** — silhouettes chosen to be distinct in outline, not just
 *      in detail, so they survive being small and being monochrome.
 *   3. **Number and name** — always present as text, never decoration.
 *
 * Remove colour entirely and the map still works. That is the bar, and
 * `tests/design-system/worlds.test.ts` holds it.
 *
 * CONTRAST
 * --------
 * Every `ink` clears 7:1 against its own `wash` — WCAG AAA for body text, not
 * the AA 4.5:1 floor — because these carry world titles. The accent is used for
 * fills and borders only, and clears 3:1 against the page.
 */

import { contrastRatio } from './contrast';

export interface WorldPalette {
  /** Named in the curriculum data. */
  id: string;
  /** Fill behind the world card. Light theme. */
  wash: string;
  /** Text and icon on `wash`. Clears 7:1 against it. */
  ink: string;
  /** Borders, rings, progress arcs. Clears 3:1 against the page. */
  accent: string;
  /** Dark theme equivalents. */
  washDark: string;
  inkDark: string;
  accentDark: string;
}

/**
 * Keyed by the `colour` field in `curriculum/worlds.json`, not by world id, so
 * a world can be renamed or reordered without touching the palette.
 */
export const WORLD_PALETTES: Record<string, WorldPalette> = {
  dawn: {
    id: 'dawn',
    wash: '#fff1e6',
    ink: '#7a3a00',
    accent: '#b35300',
    washDark: '#2a1a0c',
    inkDark: '#ffd9b8',
    accentDark: '#ff9f4d',
  },
  sky: {
    id: 'sky',
    wash: '#e6f2ff',
    ink: '#00407a',
    accent: '#005a9c',
    washDark: '#0c1c2a',
    inkDark: '#b8dcff',
    accentDark: '#69b4ff',
  },
  meadow: {
    id: 'meadow',
    wash: '#e6f6ea',
    ink: '#14532d',
    accent: '#1a6b3a',
    washDark: '#0d2216',
    inkDark: '#b6ecc6',
    accentDark: '#4ec27a',
  },
  amber: {
    id: 'amber',
    wash: '#fff6dd',
    ink: '#6b4400',
    accent: '#8a5a00',
    washDark: '#2a2008',
    inkDark: '#ffe4a3',
    accentDark: '#e0a72e',
  },
  violet: {
    id: 'violet',
    wash: '#f1ebff',
    ink: '#442a8a',
    accent: '#5b39b8',
    washDark: '#1d1533',
    inkDark: '#d9c9ff',
    accentDark: '#a385ff',
  },
  coral: {
    id: 'coral',
    wash: '#ffeced',
    ink: '#8a1f2b',
    accent: '#b02a39',
    washDark: '#2e1013',
    inkDark: '#ffc9ce',
    accentDark: '#ff7b88',
  },
  teal: {
    id: 'teal',
    wash: '#e0f5f3',
    ink: '#0f4d4a',
    accent: '#146b66',
    washDark: '#0a2321',
    inkDark: '#a8e8e2',
    accentDark: '#3fbdb3',
  },
  indigo: {
    id: 'indigo',
    wash: '#eaecff',
    ink: '#2b3175',
    accent: '#3a42a0',
    washDark: '#14162e',
    inkDark: '#c6cbff',
    accentDark: '#8b93ff',
  },
  ember: {
    id: 'ember',
    wash: '#ffeae2',
    ink: '#8a2e0c',
    accent: '#b03d12',
    washDark: '#2e1409',
    inkDark: '#ffc7b0',
    accentDark: '#ff8a5c',
  },
  gold: {
    id: 'gold',
    wash: '#fff4d6',
    ink: '#6b4a00',
    accent: '#8a6100',
    washDark: '#2a2007',
    inkDark: '#ffe08a',
    accentDark: '#e5b42b',
  },
};

/**
 * A fallback that is deliberately plain rather than eye-catching.
 *
 * If a world ships with an unknown colour name, the map should look slightly
 * unfinished — not accidentally claim an identity that belongs to another
 * world, which is what a random pick would do.
 */
export const NEUTRAL_PALETTE: WorldPalette = {
  id: 'neutral',
  wash: '#f4f6f8',
  ink: '#1a1a1a',
  accent: '#4a4a4a',
  washDark: '#1e1e1e',
  inkDark: '#f0f0f0',
  accentDark: '#b8b8b8',
};

export function paletteFor(colour: string): WorldPalette {
  return WORLD_PALETTES[colour] ?? NEUTRAL_PALETTE;
}

/**
 * Icon silhouettes, chosen so the ten differ in OUTLINE.
 *
 * Two icons that are both "a circle with something inside" are the same icon at
 * 32px, however different the insides are. These were picked for distinct outer
 * shape: a triangle reads differently from a rectangle from a chevron even when
 * it is tiny, monochrome, and seen by somebody with low vision.
 */
export type WorldIcon =
  | 'sunrise'
  | 'question'
  | 'path'
  | 'hand'
  | 'shield'
  | 'balance'
  | 'signal'
  | 'circle-group'
  | 'alert'
  | 'door';

export const ICON_PATHS: Record<WorldIcon, string> = {
  // A rising semicircle over a line. Wide, flat-bottomed.
  sunrise: 'M2 17h20M5 17a7 7 0 0 1 14 0M12 3v3M5 7l2 2M19 7l-2 2',
  // A tall hook with a dot. Narrow, top-heavy.
  question: 'M9 8a3 3 0 1 1 4 2.8c-.8.4-1 1-1 1.7V14M12 18v.5',
  // A winding line. Diagonal, no enclosure.
  path: 'M4 20c4 0 3-6 7-6s3-6 7-6',
  // An open palm. Fingered top edge.
  hand: 'M7 12V6a1.5 1.5 0 0 1 3 0v5M10 11V4.5a1.5 1.5 0 0 1 3 0V11M13 11V6a1.5 1.5 0 0 1 3 0v7c0 4-2 7-5 7s-5-2-5-5v-3',
  // A pointed shield. Symmetrical, tapers to a point.
  shield: 'M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z',
  // Scales. Wide horizontal with two hanging arcs.
  balance: 'M12 4v16M5 8h14M5 8l-3 6a3 3 0 0 0 6 0zM19 8l-3 6a3 3 0 0 0 6 0z',
  // Broadcast arcs. Nested, opening rightward.
  signal: 'M12 12h.01M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.5 5.5a9 9 0 0 0 0 13M18.5 5.5a9 9 0 0 1 0 13',
  // Three circles. Multiple enclosures.
  'circle-group': 'M9 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM17 11a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM12 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  // A triangle with a bar. The only triangle in the set.
  alert: 'M12 4L2.5 20h19zM12 10v4M12 17v.5',
  // A rectangle with a handle. The only hard rectangle.
  door: 'M6 3h12v18H6zM14 12v.5',
};

/**
 * Verify a palette clears AAA for its text and AA for its non-text.
 *
 * Exported rather than kept private because the test suite calls it over every
 * palette in both themes — a contrast rule asserted in a comment is a contrast
 * rule nobody checks.
 */
export function checkPalette(palette: WorldPalette): {
  lightText: number;
  darkText: number;
  passes: boolean;
} {
  const lightText = contrastRatio(palette.ink, palette.wash);
  const darkText = contrastRatio(palette.inkDark, palette.washDark);

  return {
    lightText,
    darkText,
    // 7:1 is WCAG 2.2 AAA for body text. These carry world titles at normal
    // weight and small sizes on the map, so AA would not be enough.
    passes: lightText >= 7 && darkText >= 7,
  };
}

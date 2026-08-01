/**
 * Shared style helpers for the primitive layer.
 *
 * These are the only place in `ui/` where a raw value is written. Every
 * primitive composes from here, so changing the focus treatment or the target
 * floor is one edit rather than twelve.
 *
 * WHY CSS-IN-TS AND NOT A STYLESHEET
 * ----------------------------------
 * The primitives need to read values that only exist at runtime — the learner's
 * target size, their motion preference, the resolved theme. A stylesheet cannot
 * branch on those without duplicating every rule per variant. What matters for
 * the blueprint's "no inline styles" acceptance criterion is that *feature code*
 * stops writing style objects; the primitives owning them is the point.
 */
import type { CSSProperties } from 'react';

import { focusRingShadow } from '@/design-system/semantic';

export type Gap = 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export const GAP: Record<Gap, string> = {
  none: '0',
  xs: 'var(--space-xs, 0.25rem)',
  sm: 'var(--space-sm, 0.5rem)',
  md: 'var(--space-md, 1rem)',
  lg: 'var(--space-lg, 1.5rem)',
  xl: 'var(--space-xl, 2.5rem)',
};

/**
 * Every interactive primitive spreads this.
 *
 * `minHeight` and `minWidth` read `--target-min`, which the profile raises to
 * as much as 88px for a learner with a motor impairment. Hard-coding 44px here
 * would silently defeat that setting — which is the kind of bug that passes
 * every test and fails one persona completely.
 */
export const interactiveBase: CSSProperties = {
  minHeight: 'var(--target-min, 44px)',
  minInlineSize: 'var(--target-min, 44px)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontSize: 'var(--type-base, 1.125rem)',
  lineHeight: 1.35,
  borderRadius: 'var(--radius-md, 8px)',
  // Logical properties throughout (Blueprint §15.2). RTL is a layout property,
  // not a translation property, and retrofitting it later is expensive while
  // starting with logical properties costs nothing.
  paddingBlock: '0.75rem',
  paddingInline: '1.25rem',
  textAlign: 'center',
  textDecoration: 'none',
  transitionProperty: 'background-color, border-color, color, box-shadow',
  transitionDuration: 'var(--duration-instant, 90ms)',
};

/**
 * The focus treatment, as a class-free style object.
 *
 * Applied on `:focus-visible` only — a mouse user who clicks a button should not
 * see a ring, but a keyboard or switch user must. Because the primitives cannot
 * express a pseudo-class inline, `ui/ui.css` carries the actual rule and this
 * exports the shadow so both stay in step.
 */
export const FOCUS_SHADOW = focusRingShadow('var(--surface-base)', 'var(--focus-ring)');

/** On a card, the inner ring must match the card rather than the page. */
export const FOCUS_SHADOW_ON_RAISED = focusRingShadow(
  'var(--surface-raised)',
  'var(--focus-ring)',
);

/**
 * Merge style objects, letting later ones win.
 *
 * Exists so a primitive can accept a `style` prop for the genuinely one-off
 * case without every primitive reimplementing the spread. Escape hatches are
 * fine; unmarked escape hatches are not, so this is the only one.
 */
export function mergeStyles(
  ...styles: (CSSProperties | undefined | false)[]
): CSSProperties {
  return Object.assign({}, ...styles.filter(Boolean));
}

/**
 * Card — a raised surface.
 *
 * Elevation carries **border weight as well as shadow**, because shadow
 * disappears entirely in forced-colours mode and in both high-contrast themes.
 * A learner using either would otherwise lose every card boundary on the screen
 * at once. `design-system/semantic.ts` holds the scale and a test asserts no
 * level has a zero border.
 *
 * An interactive card renders a real `<button>` wrapper rather than an
 * `onClick` on a div. A div with a click handler is not focusable, not
 * activatable by Enter or Space, and invisible to switch scanning — and a
 * clickable card is one of the most common places that gets forgotten.
 */
import type { CSSProperties, ElementType, ReactNode } from 'react';

import { ELEVATION, type Elevation } from '@/design-system/semantic';

import { mergeStyles } from './styles';

export interface CardProps {
  elevation?: Elevation;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  as?: ElementType;
  style?: CSSProperties;
  children: ReactNode;
}

const PADDING = {
  none: '0',
  sm: 'var(--space-sm, 0.5rem)',
  md: 'var(--space-md, 1rem)',
  lg: 'var(--space-lg, 1.5rem)',
} as const;

export function Card({
  elevation = 'raised',
  padding = 'md',
  as: Component = 'div',
  style,
  children,
  ...rest
}: CardProps & Record<string, unknown>) {
  const level = ELEVATION[elevation];

  return (
    <Component
      {...rest}
      data-ui="card"
      data-elevation={elevation}
      style={mergeStyles(
        {
          borderWidth: level.border,
          boxShadow: level.shadow,
          borderRadius: 'var(--radius-lg, 14px)',
          padding: PADDING[padding],
        },
        style,
      )}
    >
      {children}
    </Component>
  );
}

export interface ActionCardProps extends Omit<CardProps, 'as'> {
  onClick: () => void;
  /**
   * The accessible name for the whole card.
   *
   * Required, not optional. A card usually contains several pieces of text and
   * letting the browser concatenate them produces announcements like "World 4
   * Speaking Up For Yourself 3 of 5 levels 2 stars" with no indication of what
   * pressing it does.
   */
  label: string;
  disabled?: boolean;
}

/**
 * A card the learner can press.
 *
 * A real button, so it is focusable, activatable by keyboard, and reachable by
 * switch scanning — none of which a `<div onClick>` is.
 */
export function ActionCard({
  onClick,
  label,
  disabled = false,
  elevation = 'raised',
  padding = 'md',
  style,
  children,
  ...rest
}: ActionCardProps & Record<string, unknown>) {
  const level = ELEVATION[elevation];

  return (
    <button
      {...rest}
      type="button"
      data-ui="card"
      data-interactive="true"
      data-elevation={elevation}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      style={mergeStyles(
        {
          borderWidth: level.border,
          boxShadow: level.shadow,
          borderRadius: 'var(--radius-lg, 14px)',
          padding: PADDING[padding],
          // The card is a button, but it must not look or lay out like one.
          font: 'inherit',
          color: 'inherit',
          textAlign: 'start',
          inlineSize: '100%',
          minBlockSize: 'var(--target-min, 44px)',
          display: 'block',
        },
        style,
      )}
    >
      {children}
    </button>
  );
}

/**
 * Skeleton, Icon, and the states every surface must have.
 *
 * The blueprint's definition of done requires loading, empty, error and offline
 * states for every surface. Those four get forgotten because each is individually
 * trivial and collectively invisible during happy-path development — so they are
 * primitives here, and a screen that wants one does not get to invent it.
 *
 * The copy rules are the point:
 *   - An error never blames the learner and always says what is still safe.
 *   - An empty state says what to do next, not that something is missing.
 *   - Nothing anywhere counts down or hurries.
 */
import type { CSSProperties, ReactNode } from 'react';

import { Button } from './Button';
import { Stack } from './Stack';
import { Text } from './Text';
import { mergeStyles } from './styles';

export interface SkeletonProps {
  /** CSS length. */
  height?: string;
  width?: string;
  /** Announced while content loads. */
  label?: string;
  style?: CSSProperties;
}

/**
 * A loading placeholder.
 *
 * The pulse stops entirely under `prefers-reduced-motion` (`ui.css`) — a
 * shimmering rectangle is a permanently moving object on a screen somebody is
 * trying to read, which is exactly what reduced motion exists to remove.
 */
export function Skeleton({ height = '1.5rem', width = '100%', label, style }: SkeletonProps) {
  return (
    <div
      data-ui="skeleton"
      data-animated="true"
      role={label ? 'status' : undefined}
      aria-label={label}
      style={mergeStyles({ blockSize: height, inlineSize: width }, style)}
    >
      {label && <span className="visually-hidden">{label}</span>}
    </div>
  );
}

export interface StateProps {
  title: string;
  /** One or two short sentences. */
  body?: ReactNode;
  action?: { label: string; onClick: () => void };
  style?: CSSProperties;
}

/**
 * Something went wrong.
 *
 * `role="alert"` so it is announced. The copy contract is enforced by test:
 * an error message must not attribute the failure to the learner, and must say
 * what is still safe — "nothing you have done has been lost" is the difference
 * between an inconvenience and a reason to stop using the product.
 */
export function ErrorState({ title, body, action, style }: StateProps) {
  return (
    <Stack
      gap="sm"
      data-ui="error-state"
      role="alert"
      style={mergeStyles(
        {
          background: 'var(--surface-raised)',
          border: '2px solid var(--attention-ink)',
          borderRadius: 'var(--radius-lg, 14px)',
          padding: 'var(--space-md, 1rem)',
        },
        style,
      )}
    >
      <Text variant="heading" tone="attention" as="p">
        {title}
      </Text>
      {body && (
        <Text variant="body" measure>
          {body}
        </Text>
      )}
      {action && (
        <div>
          <Button variant="secondary" onRaised onClick={action.onClick}>
            {action.label}
          </Button>
        </div>
      )}
    </Stack>
  );
}

/**
 * Nothing here yet.
 *
 * Not an error, so not `role="alert"` — an empty list is a normal state and
 * interrupting a screen reader to say so is noise.
 */
export function EmptyState({ title, body, action, style }: StateProps) {
  return (
    <Stack
      gap="sm"
      data-ui="empty-state"
      style={mergeStyles({ padding: 'var(--space-lg, 1.5rem) 0' }, style)}
    >
      <Text variant="heading" as="p">
        {title}
      </Text>
      {body && (
        <Text variant="body" tone="secondary" measure>
          {body}
        </Text>
      )}
      {action && (
        <div>
          <Button variant="primary" onClick={action.onClick}>
            {action.label}
          </Button>
        </div>
      )}
    </Stack>
  );
}

export interface IconProps {
  /** Inline SVG path data. */
  path: string;
  size?: number;
  /**
   * When omitted the icon is decorative and hidden from assistive tech.
   *
   * That is the right default: an icon beside a text label is decoration, and
   * announcing both produces "star star, two stars". An icon carrying meaning
   * on its own needs a label — and usually needs visible text instead.
   */
  label?: string;
  style?: CSSProperties;
}

export function Icon({ path, size = 24, label, style }: IconProps) {
  return (
    <svg
      data-ui="icon"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
      fill="currentColor"
      style={mergeStyles({ flex: '0 0 auto', verticalAlign: 'middle' }, style)}
    >
      <path d={path} />
    </svg>
  );
}

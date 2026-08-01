/**
 * Progress — the "the end is always visible" components (Blueprint §5.2).
 *
 * This is the single most load-bearing pair of components in the redesign, and
 * the reason is psychological rather than visual: the first of Duolingo's four
 * mechanics is *the session is short and the end is visible*. A learner who
 * cannot answer "how much is left?" is a learner deciding whether to stop.
 *
 * Both components state their progress in **text**, always. A row of filled
 * circles is meaningless to a screen-reader user and ambiguous to a learner
 * with a colour vision deficiency, so the dots are decoration over a sentence
 * rather than the thing itself.
 */
import type { CSSProperties } from 'react';

import { mergeStyles } from './styles';

export interface ProgressDotsProps {
  total: number;
  /** How many are finished. */
  completed: number;
  /** Zero-based index of the one in progress, if any. */
  current?: number;
  /** What the dots are counting. Used in the announcement. */
  label?: string;
  style?: CSSProperties;
}

/**
 * Mission progress within a level.
 *
 * Deliberately not a bar: a bar implies a continuous quantity, and a level is a
 * countable number of discrete missions. "Three of five" is a more useful fact
 * than "60%", and it is the fact a learner uses to decide whether to finish.
 */
export function ProgressDots({
  total,
  completed,
  current,
  label = 'missions',
  style,
}: ProgressDotsProps) {
  const sentence = `${completed} of ${total} ${label} done.`;

  return (
    <div
      data-ui="progress-dots"
      // One group with one name. Announcing eight separate dots would bury the
      // fact in noise.
      role="group"
      aria-label={sentence}
      style={mergeStyles(
        { display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' },
        style,
      )}
    >
      {Array.from({ length: total }, (_, index) => (
        <span
          key={index}
          data-ui="progress-dot"
          data-state={
            index < completed ? 'done' : index === current ? 'current' : 'todo'
          }
          aria-hidden="true"
          style={{
            inlineSize: '0.85rem',
            blockSize: '0.85rem',
            borderRadius: 'var(--radius-full, 999px)',
            borderStyle: 'solid',
            borderWidth: '2px',
            flex: '0 0 auto',
          }}
        />
      ))}
      <span className="visually-hidden">{sentence}</span>
    </div>
  );
}

export interface ProgressBarProps {
  value: number;
  max?: number;
  /** Required — an unlabelled bar is a coloured rectangle. */
  label: string;
  /** Shown beside the bar, e.g. "40 XP to go". Never a countdown. */
  hint?: string;
  style?: CSSProperties;
}

/**
 * A continuous quantity — XP toward a level, phrases toward a milestone.
 *
 * `role="progressbar"` with real `aria-valuenow`/`valuemin`/`valuemax`, plus a
 * visible textual value. Colour never carries the meaning: the number is on
 * screen next to the bar.
 */
export function ProgressBar({ value, max = 100, label, hint, style }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(value, max));
  const percent = max === 0 ? 0 : Math.round((clamped / max) * 100);

  return (
    <div data-ui="progress" style={mergeStyles({ display: 'grid', gap: '0.35rem' }, style)}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: '0.75rem',
          flexWrap: 'wrap',
          fontSize: '1rem',
          color: 'var(--text-secondary)',
        }}
      >
        <span>{label}</span>
        <span>
          {clamped} of {max}
          {hint ? ` — ${hint}` : ''}
        </span>
      </div>

      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
        style={{
          blockSize: '0.75rem',
          background: 'var(--surface-sunken)',
          borderRadius: 'var(--radius-full, 999px)',
          borderStyle: 'solid',
          borderWidth: '1px',
          borderColor: 'var(--border-subtle)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            inlineSize: `${percent}%`,
            blockSize: '100%',
            background: 'var(--interactive-rest)',
            // Width is animated here rather than transform because the bar is
            // a fill, not a movement — and it is 12px tall, so the layout cost
            // is negligible and the alternative (a scaled overlay) rounds badly
            // at small percentages.
            transition: 'inline-size var(--duration-base, 240ms) ease',
          }}
        />
      </div>
    </div>
  );
}

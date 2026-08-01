/**
 * Field — a labelled input, with the association guaranteed.
 *
 * The single most common accessibility defect in web forms is a label that is
 * visually adjacent to an input and not programmatically associated with it. A
 * screen reader then announces "edit text, blank" and the learner has no way to
 * know what to type.
 *
 * This primitive makes the association structural: the id is generated here,
 * the label always uses it, and hint and error text are wired through
 * `aria-describedby` automatically. A caller cannot forget because a caller
 * never does it.
 *
 * An error is announced via `role="alert"` and is *also* marked on the control
 * with `aria-invalid`. Colour is never the signal — the message is text.
 */
import { useId, type CSSProperties, type InputHTMLAttributes, type ReactNode } from 'react';

import { mergeStyles } from './styles';

export interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> {
  label: ReactNode;
  /** Guidance shown before the learner types, e.g. an example. */
  hint?: ReactNode;
  /** Shown and announced when present. */
  error?: string;
  style?: CSSProperties;
}

export function Field({ label, hint, error, style, id, ...rest }: FieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;

  const describedBy = [hint ? hintId : null, error ? errorId : null]
    .filter(Boolean)
    .join(' ');

  return (
    <div data-ui="field" style={mergeStyles({ display: 'grid', gap: '0.35rem' }, style)}>
      <label htmlFor={fieldId} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
        {label}
      </label>

      {hint && (
        <span id={hintId} style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
          {hint}
        </span>
      )}

      <input
        {...rest}
        id={fieldId}
        data-ui="input"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        style={{
          minBlockSize: 'var(--target-min, 44px)',
          font: 'inherit',
          color: 'var(--text-primary)',
          background: 'var(--surface-base)',
          borderStyle: 'solid',
          borderWidth: error ? '2px' : '1px',
          borderColor: error ? 'var(--attention-ink)' : 'var(--border-strong)',
          borderRadius: 'var(--radius-md, 8px)',
          paddingInline: '0.75rem',
          paddingBlock: '0.5rem',
          inlineSize: '100%',
        }}
      />

      {error && (
        <span
          id={errorId}
          role="alert"
          style={{ color: 'var(--attention-ink)', fontSize: '1rem' }}
        >
          {error}
        </span>
      )}
    </div>
  );
}

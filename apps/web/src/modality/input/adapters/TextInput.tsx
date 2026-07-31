/**
 * Typed input.
 *
 * Serves P2 (Deaf), P5 (stammer) and anyone whose speech is not being
 * recognised reliably today. Not a lossy mode, so it emits no confidence and is
 * never sent for confirmation.
 *
 * There is no character limit and no timer. The submit button stays enabled
 * regardless of how long the learner takes (Ethics E6).
 */
import { useRef, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

import type { InputAdapterProps } from '../registry';
import { buildResponse } from '../response';

export function TextInput({
  block,
  profile,
  sessionId,
  onResponse,
  disabled,
}: InputAdapterProps) {
  const [value, setValue] = useState('');
  const [attempts, setAttempts] = useState(1);
  const startedAt = useRef(new Date());
  const announce = useAnnounce();

  const fieldId = `answer-${block.id}`;
  const hintId = `${fieldId}-hint`;
  const empty = value.trim().length === 0;

  const submit = () => {
    if (empty || disabled) return;

    onResponse(
      buildResponse({
        block,
        profile,
        sessionId,
        inputMode: 'text',
        text: value,
        startedAt: startedAt.current,
        attempts,
        raw: { typed_text: value },
      }),
    );

    announce('Answer sent');
    setAttempts((n) => n + 1);
    setValue('');
    startedAt.current = new Date();
  };

  return (
    <div data-input-mode="text">
      <label htmlFor={fieldId} style={{ display: 'block', fontWeight: 700, marginBottom: '0.5rem' }}>
        Your answer
      </label>

      <p id={hintId} style={{ margin: '0 0 0.5rem', color: 'var(--colour-fg-muted)' }}>
        Take as long as you need. There is no time limit.
      </p>

      <textarea
        id={fieldId}
        aria-describedby={hintId}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={3}
        // Deliberately NOT submit-on-Enter: a learner using switch access or a
        // head pointer hits Enter accidentally, and losing a half-typed answer
        // is far more costly than one extra button press.
        style={{
          width: '100%',
          font: 'inherit',
          padding: 'var(--space-sm, 0.5rem)',
          color: 'var(--colour-fg)',
          background: 'var(--colour-bg)',
          border: '1px solid var(--colour-border)',
          borderRadius: 'var(--radius-md, 8px)',
        }}
      />

      <button
        type="button"
        onClick={submit}
        disabled={empty || disabled}
        style={submitButtonStyle(empty || Boolean(disabled))}
      >
        Send answer
      </button>
    </div>
  );
}

export function submitButtonStyle(isDisabled: boolean) {
  return {
    marginTop: 'var(--space-sm, 0.5rem)',
    minHeight: 'var(--target-min, 44px)',
    padding: '0 var(--space-lg, 1.5rem)',
    border: '1px solid var(--colour-border)',
    borderRadius: 'var(--radius-md, 8px)',
    background: isDisabled ? 'var(--colour-surface)' : 'var(--colour-accent)',
    color: isDisabled ? 'var(--colour-fg-muted)' : 'var(--colour-accent-fg)',
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    fontWeight: 700,
  } as const;
}

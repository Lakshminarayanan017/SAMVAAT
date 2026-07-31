/**
 * AAC symbol board — compose an answer by tapping picture symbols.
 *
 * Primary input for P4 (Fatima), and the reason a non-speaking learner can sit a
 * full mock interview as a first-class path rather than a degraded fallback.
 * The composed symbols become `canonical_text`, so the answer flows through
 * exactly the same scoring, scheduling and dashboards as a spoken one
 * (ADR-0002).
 *
 * Layout follows AAC convention: core vocabulary (high-frequency words, stable
 * position) first, then fringe vocabulary drawn from the block itself. Stable
 * position matters — AAC users build motor memory for symbol locations, and
 * reshuffling the board between screens destroys it.
 */
import { useRef, useState } from 'react';
import type { Pictograph } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';

import type { InputAdapterProps } from '../registry';
import { buildResponse } from '../response';
import { submitButtonStyle } from './TextInput';

/**
 * Core vocabulary. Fixed order, always present, never reordered.
 * Sourced from the ARASAAC set; ids are placeholders until the asset pipeline
 * lands in M3.
 */
const CORE_VOCABULARY: Pictograph[] = [
  { set: 'arasaac', id: 6625, label: 'I' },
  { set: 'arasaac', id: 8146, label: 'you' },
  { set: 'arasaac', id: 8043, label: 'want' },
  { set: 'arasaac', id: 6009, label: 'need' },
  { set: 'arasaac', id: 5441, label: 'help' },
  { set: 'arasaac', id: 7095, label: 'please' },
  { set: 'arasaac', id: 6510, label: 'thank you' },
  { set: 'arasaac', id: 5584, label: 'yes' },
  { set: 'arasaac', id: 5526, label: 'no' },
  { set: 'arasaac', id: 8071, label: 'work' },
  { set: 'arasaac', id: 6479, label: 'good' },
  { set: 'arasaac', id: 11317, label: 'again' },
];

export function AacBoardInput({
  block,
  profile,
  sessionId,
  onResponse,
  disabled,
}: InputAdapterProps) {
  const [selected, setSelected] = useState<Pictograph[]>([]);
  const [attempts, setAttempts] = useState(1);
  const startedAt = useRef(new Date());
  const announce = useAnnounce();

  const fringe = block.representations?.pictographs ?? [];

  // Core vocabulary never repeats a symbol already offered for this lesson.
  // The same picture appearing twice on one board is genuinely confusing for an
  // AAC user, and it breaks the positional motor memory the layout depends on.
  const fringeLabels = new Set(fringe.map((symbol) => symbol.label.toLowerCase()));
  const core = CORE_VOCABULARY.filter((symbol) => !fringeLabels.has(symbol.label.toLowerCase()));
  const sentence = selected.map((s) => s.label).join(' ');
  const empty = selected.length === 0;

  const add = (symbol: Pictograph) => {
    setSelected((current) => [...current, symbol]);
    // Announced so a learner using both symbols and a screen reader hears the
    // sentence build, rather than only seeing it.
    announce(symbol.label);
  };

  const removeLast = () => {
    setSelected((current) => {
      const last = current.at(-1);
      if (last) announce(`Removed ${last.label}`);
      return current.slice(0, -1);
    });
  };

  const submit = () => {
    if (empty || disabled) return;

    onResponse(
      buildResponse({
        block,
        profile,
        sessionId,
        inputMode: 'aac',
        text: sentence,
        startedAt: startedAt.current,
        attempts,
        // Symbol selection is unambiguous: the learner picked exactly this.
        confidence: 1,
        raw: { symbol_sequence: selected.map((s) => s.id) },
      }),
    );

    announce('Answer sent');
    setAttempts((n) => n + 1);
    setSelected([]);
    startedAt.current = new Date();
  };

  return (
    <div data-input-mode="aac">
      {/* ── Sentence bar ─────────────────────────────────────────────────── */}
      <div
        role="status"
        aria-live="polite"
        aria-label="Your sentence"
        style={{
          minHeight: 'calc(var(--target-min, 44px) * 1.5)',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
          padding: 'var(--space-sm, 0.5rem)',
          border: '2px solid var(--colour-border)',
          borderRadius: 'var(--radius-md, 8px)',
          background: 'var(--colour-bg)',
          marginBottom: 'var(--space-md, 1rem)',
        }}
      >
        {empty ? (
          <span style={{ color: 'var(--colour-fg-muted)' }}>Tap pictures to build your answer</span>
        ) : (
          selected.map((symbol, index) => (
            <span
              key={`${symbol.id}-${index}`}
              style={{
                padding: '0.25rem 0.5rem',
                borderRadius: 'var(--radius-sm, 4px)',
                background: 'var(--colour-surface)',
                border: '1px solid var(--colour-border)',
              }}
            >
              {symbol.label}
            </span>
          ))
        )}
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-sm, 0.5rem)', marginBottom: 'var(--space-md, 1rem)' }}>
        <button type="button" onClick={removeLast} disabled={empty} style={secondaryButtonStyle}>
          Undo
        </button>
        <button
          type="button"
          onClick={() => {
            setSelected([]);
            announce('Cleared');
          }}
          disabled={empty}
          style={secondaryButtonStyle}
        >
          Clear all
        </button>
      </div>

      {fringe.length > 0 && (
        <SymbolGroup label="Words for this lesson" symbols={fringe} onSelect={add} disabled={disabled} />
      )}
      <SymbolGroup label="Words I use often" symbols={core} onSelect={add} disabled={disabled} />

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

function SymbolGroup({
  label,
  symbols,
  onSelect,
  disabled,
}: {
  label: string;
  symbols: Pictograph[];
  onSelect: (symbol: Pictograph) => void;
  disabled?: boolean;
}) {
  const groupId = `aac-group-${label.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <section aria-labelledby={groupId} style={{ marginBottom: 'var(--space-md, 1rem)' }}>
      <h3 id={groupId} style={{ fontSize: '1rem', margin: '0 0 var(--space-sm, 0.5rem)' }}>
        {label}
      </h3>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(6rem, 1fr))',
          gap: 'var(--space-sm, 0.5rem)',
        }}
      >
        {symbols.map((symbol, index) => (
          <button
            key={`${symbol.set}-${symbol.id}-${index}`}
            type="button"
            onClick={() => onSelect(symbol)}
            disabled={disabled}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.25rem',
              // Comfortably above the 44px floor: AAC users often have motor
              // impairments alongside, and these are the most-tapped controls
              // in the product.
              minHeight: 'calc(var(--target-min, 44px) * 1.6)',
              padding: 'var(--space-sm, 0.5rem)',
              border: '1px solid var(--colour-border)',
              borderRadius: 'var(--radius-md, 8px)',
              background: 'var(--colour-surface)',
              color: 'var(--colour-fg)',
              cursor: disabled ? 'not-allowed' : 'pointer',
            }}
          >
            {symbol.uri ? (
              <img src={symbol.uri} alt="" width={48} height={48} aria-hidden="true" />
            ) : (
              <span aria-hidden="true" style={{ fontSize: '1.5rem', lineHeight: 1 }}>
                ▢
              </span>
            )}
            <span style={{ fontSize: '0.95rem' }}>{symbol.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

const secondaryButtonStyle = {
  minHeight: 'var(--target-min, 44px)',
  padding: '0 var(--space-md, 1rem)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  cursor: 'pointer',
} as const;

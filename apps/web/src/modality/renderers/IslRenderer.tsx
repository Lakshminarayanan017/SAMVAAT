/**
 * An Indian Sign Language clip, with its gloss.
 *
 * Primary channel for P2 (Deaf), whose first language is ISL and whose written
 * English is a second language — so text alone is not equivalent access.
 *
 * These are recorded human signers, not a generated avatar. ISL grammar is not
 * English word order, and a synthetic avatar producing English-ordered signs is
 * worse than no avatar: it looks like access while communicating nonsense. The
 * 3D avatar is explicitly deferred (docs/EXECUTION_PLAN.md §3.2).
 *
 * `loop` and a slower rate are offered because sign, unlike text, cannot be
 * re-read at the viewer's own pace without them.
 */
import { useRef, useState } from 'react';

import type { RendererProps } from '../registry';

const RATES = [0.5, 0.75, 1] as const;

export function IslRenderer({ block }: RendererProps) {
  const clip = block.representations?.isl_clip;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [rate, setRate] = useState<number>(1);

  if (!clip) return null;

  const changeRate = (next: number) => {
    setRate(next);
    if (videoRef.current) videoRef.current.playbackRate = next;
  };

  return (
    <div data-channel="isl">
      <video
        ref={videoRef}
        src={clip.uri}
        controls
        loop
        playsInline
        preload="none"
        aria-label={`Indian Sign Language: ${block.canonical_text}`}
        style={{
          width: '100%',
          maxWidth: '22rem',
          borderRadius: 'var(--radius-md, 8px)',
          background: 'var(--colour-surface)',
        }}
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm, 0.5rem)',
          marginTop: 'var(--space-sm, 0.5rem)',
        }}
      >
        <span id={`isl-rate-${block.id}`} style={{ fontSize: '0.95rem' }}>
          Speed
        </span>
        <div role="group" aria-labelledby={`isl-rate-${block.id}`} style={{ display: 'flex', gap: '0.25rem' }}>
          {RATES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => changeRate(option)}
              aria-pressed={rate === option}
              style={{
                minWidth: 'var(--target-min, 44px)',
                minHeight: 'var(--target-min, 44px)',
                border: '1px solid var(--colour-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                background: rate === option ? 'var(--colour-accent)' : 'var(--colour-surface)',
                color: rate === option ? 'var(--colour-accent-fg)' : 'var(--colour-fg)',
                cursor: 'pointer',
              }}
            >
              {option}×
            </button>
          ))}
        </div>
      </div>

      {/* The gloss records the actual signed sequence, which differs from the
          English sentence. Shown because ISL learners and interpreters use it. */}
      <p
        style={{
          margin: 'var(--space-sm, 0.5rem) 0 0 0',
          fontSize: '0.95rem',
          color: 'var(--colour-fg-muted)',
          fontFamily: 'ui-monospace, monospace',
        }}
      >
        <span style={{ fontFamily: 'inherit' }}>ISL gloss: </span>
        {clip.gloss}
      </p>
    </div>
  );
}

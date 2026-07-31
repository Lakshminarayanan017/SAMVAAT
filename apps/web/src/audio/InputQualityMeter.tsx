/**
 * The microphone quality indicator.
 *
 * A level meter is the classic sighted-only control: a bar that moves, meaning
 * nothing to a screen-reader user and nothing to anyone who cannot interpret it.
 * This carries the same information four ways at once — a bar, a text verdict,
 * a live-region announcement, and a numeric value on the progressbar role.
 *
 * Announcements are throttled and only fire when the verdict CHANGES. A meter
 * that announces every frame is worse than no meter at all: it makes the page
 * unusable with a screen reader, and it is a mistake that looks like diligence.
 */
import { useEffect, useRef } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

import type { QualityAssessment, QualityVerdict } from './quality';

const VERDICT_COLOUR: Record<QualityVerdict, string> = {
  good: 'var(--colour-accent)',
  quiet: 'var(--colour-fg-muted)',
  loud: 'var(--colour-fg-muted)',
  noisy: 'var(--colour-fg-muted)',
  silent: 'var(--colour-fg-muted)',
};

export function InputQualityMeter({ quality }: { quality: QualityAssessment | null }) {
  const announce = useAnnounce();
  const lastVerdict = useRef<QualityVerdict | null>(null);

  useEffect(() => {
    if (!quality) return;
    if (quality.verdict === lastVerdict.current) return;

    lastVerdict.current = quality.verdict;
    // Polite: a microphone hint must never interrupt what the learner is doing.
    announce(quality.message, 'polite');
  }, [quality, announce]);

  if (!quality) return null;

  const percent = Math.min(100, Math.round(quality.reading.level * 300));

  return (
    <div data-testid="input-quality" data-verdict={quality.verdict}>
      {/* The bar. Decorative duplicate of the text below, so it is hidden from
          assistive tech rather than read as a second, confusing value. */}
      <div
        aria-hidden="true"
        style={{
          height: '0.75rem',
          background: 'var(--colour-surface)',
          border: '1px solid var(--colour-border)',
          borderRadius: 'var(--radius-sm, 4px)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${percent}%`,
            height: '100%',
            background: VERDICT_COLOUR[quality.verdict],
            // No transition: this is a live measurement, and animating it would
            // make it lag behind what the learner is actually doing.
          }}
        />
      </div>

      {/* The same measurement, exposed properly. */}
      <div
        role="progressbar"
        aria-label="Microphone level"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${percent} percent. ${quality.message}`}
        style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clipPath: 'inset(50%)' }}
      />

      <p
        style={{
          margin: 'var(--space-sm, 0.5rem) 0 0',
          color: quality.verdict === 'good' ? 'var(--colour-fg)' : 'var(--colour-fg-muted)',
        }}
      >
        {quality.message}
      </p>
    </div>
  );
}

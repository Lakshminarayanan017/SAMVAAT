/**
 * Narrated audio, with the transcript always visible.
 *
 * Primary channel for P1 (low vision).
 *
 * Two deliberate choices:
 *
 *   * The transcript is always rendered, never hidden behind a toggle. A
 *     learner who cannot hear it and a learner who cannot see it are both
 *     served by the same markup, and neither has to discover a control.
 *
 *   * When the profile asks for slower speech we prefer the recorded slow
 *     track over `playbackRate`. Time-stretching pitch-shifts and smears
 *     consonants, which is precisely the detail a pronunciation learner needs.
 */
import { useEffect, useRef } from 'react';

import type { RendererProps } from '../registry';

export function AudioRenderer({ block, profile, isSupport }: RendererProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const rate = profile.presentation?.audio_rate ?? 1.0;

  const native = block.representations?.audio_native;
  const slow = block.representations?.audio_slow;

  const wantsSlow = rate < 1.0;
  const track = wantsSlow && slow ? slow : native;
  // Only fall back to time-stretching when no recorded slow track exists.
  const playbackRate = wantsSlow && !slow ? rate : 1.0;

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = playbackRate;
  }, [playbackRate, track?.uri]);

  const transcript = block.representations?.caption ?? block.canonical_text;

  if (!track) return null;

  return (
    <div data-channel="audio">
      <audio
        ref={audioRef}
        src={track.uri}
        controls
        preload="none"
        // Names the control for screen readers and voice control, which would
        // otherwise announce an unlabelled "audio player".
        aria-label={`Listen: ${transcript}`}
        style={{ width: '100%', maxWidth: '32rem' }}
      >
        <track kind="captions" />
      </audio>

      <p
        style={{
          margin: 'var(--space-sm, 0.5rem) 0 0 0',
          fontSize: isSupport ? 'var(--type-sm, 1rem)' : 'var(--type-base, 1.125rem)',
          color: 'var(--colour-fg-muted)',
        }}
      >
        {transcript}
      </p>

      {wantsSlow && !slow && (
        // Surfaced rather than silently degraded: a missing slow recording is a
        // content gap the team should see, and the learner deserves to know why
        // the audio sounds different from usual.
        <p style={{ fontSize: '0.9rem', color: 'var(--colour-fg-muted)', margin: '0.25rem 0 0' }}>
          Slowed automatically — no slow recording available yet.
        </p>
      )}
    </div>
  );
}

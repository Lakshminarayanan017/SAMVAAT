/**
 * Text with captions — the floor of the fallback chain.
 *
 * Every block has `canonical_text`, so this renderer can always produce
 * something. That guarantee is what lets `resolveChannel` promise a learner
 * never sees an empty screen.
 *
 * Primary channel for P2 (Deaf) and reachable by screen reader for P1.
 */
import type { RendererProps } from '../registry';

export function CaptionedTextRenderer({ block, isSupport }: RendererProps) {
  const text = block.representations?.caption ?? block.canonical_text;

  return (
    <p
      data-channel="captioned_text"
      lang="en-IN"
      style={{
        margin: 0,
        fontSize: isSupport ? 'var(--type-sm, 1rem)' : 'var(--type-lg, 1.375rem)',
        lineHeight: 1.6,
        color: isSupport ? 'var(--colour-fg-muted)' : 'var(--colour-fg)',
      }}
    >
      {text}
    </p>
  );
}

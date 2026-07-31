/**
 * A pictograph strip — one symbol per idea, each with its text label.
 *
 * Support channel for P4 (intellectual disability), usually shown beneath
 * Easy-Read text.
 *
 * Labels are always visible, never `alt`-only. A learner using symbols is often
 * also building literacy, and pairing the symbol with the word is the point.
 * `role="img"` with a composed label makes the strip read as one unit to a
 * screen reader rather than as a stream of disconnected words.
 */
import type { RendererProps } from '../registry';

export function PictographRenderer({ block }: RendererProps) {
  const pictographs = block.representations?.pictographs ?? [];
  if (!pictographs.length) return null;

  const spokenLabel = pictographs.map((p) => p.label).join(', ');

  return (
    <ul
      data-channel="pictograph"
      role="img"
      aria-label={`Symbols: ${spokenLabel}`}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 'var(--space-sm, 0.5rem)',
        listStyle: 'none',
        margin: 0,
        padding: 0,
      }}
    >
      {pictographs.map((pictograph, index) => (
        <li
          key={`${pictograph.set}-${pictograph.id}-${index}`}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.25rem',
            minWidth: 'var(--target-min, 44px)',
            padding: 'var(--space-xs, 0.25rem)',
            border: '1px solid var(--colour-border)',
            borderRadius: 'var(--radius-md, 8px)',
            background: 'var(--colour-surface)',
          }}
        >
          {pictograph.uri ? (
            <img src={pictograph.uri} alt="" width={56} height={56} aria-hidden="true" />
          ) : (
            // Placeholder until the ARASAAC asset pipeline lands (M3). Marked
            // aria-hidden so it never reaches a screen reader as content.
            <span
              aria-hidden="true"
              style={{
                width: 56,
                height: 56,
                display: 'grid',
                placeItems: 'center',
                border: '1px dashed var(--colour-border)',
                borderRadius: 'var(--radius-sm, 4px)',
                color: 'var(--colour-fg-muted)',
                fontSize: '0.75rem',
              }}
            >
              ▢
            </span>
          )}
          <span style={{ fontSize: '0.95rem', color: 'var(--colour-fg)' }}>
            {pictograph.label}
          </span>
        </li>
      ))}
    </ul>
  );
}

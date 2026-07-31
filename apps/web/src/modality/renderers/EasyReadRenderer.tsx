/**
 * Easy-Read text — one idea per line, large type, generous spacing.
 *
 * Primary channel for P4 (intellectual disability).
 *
 * The source text is authored with a line break per idea and the content
 * validator enforces at most 15 words per sentence (rule A11Y-5), so this
 * renderer splits on newlines rather than trying to simplify anything itself.
 * Simplification is a human editorial job, not a runtime transformation.
 */
import type { RendererProps } from '../registry';

export function EasyReadRenderer({ block, isSupport }: RendererProps) {
  const source = block.representations?.easy_read ?? block.canonical_text;
  const lines = source.split('\n').filter((line) => line.trim());

  return (
    <div data-channel="easy_read">
      {lines.map((line, index) => (
        <p
          key={index}
          style={{
            margin: '0 0 var(--space-md, 1rem) 0',
            fontSize: isSupport ? 'var(--type-base, 1.125rem)' : 'var(--type-xl, 1.75rem)',
            lineHeight: 1.8,
            // Never justified: uneven word spacing creates "rivers" that are a
            // documented reading barrier for dyslexic and low-vision readers.
            textAlign: 'left',
            maxWidth: '30ch',
            color: 'var(--colour-fg)',
          }}
        >
          {line.trim()}
        </p>
      ))}
    </div>
  );
}

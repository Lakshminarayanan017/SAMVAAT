/**
 * The channel comparison view — milestone MS2's proof screen.
 *
 * One authored ContentBlock, rendered simultaneously through all five output
 * channels, beside a switcher for the five personas. It exists to make the
 * central architectural claim visible in a single screenshot: accessibility is
 * not a setting on this product, it is the shape of the product.
 *
 * This is a development and demonstration surface. It is the ONLY place allowed
 * to pass `forceChannel` to the router — production feature code always lets the
 * learner's profile decide.
 */
import { useState } from 'react';
import type {
  CommunicationAbilityProfile,
  ContentBlock,
  LearnerResponse,
  OutputChannel,
} from '@samvaad/contracts';

import { ProfileProvider } from '@/a11y/ProfileProvider';
import { ModalityInput, ModalityRouter } from '@/modality';

import { PERSONAS, type Persona } from './personas';

const CHANNELS: { channel: OutputChannel; label: string; serves: string }[] = [
  { channel: 'captioned_text', label: 'Text', serves: 'P2, P5' },
  { channel: 'audio', label: 'Audio', serves: 'P1' },
  { channel: 'easy_read', label: 'Easy-Read', serves: 'P4' },
  { channel: 'pictograph', label: 'Picture symbols', serves: 'P4' },
  { channel: 'isl', label: 'Indian Sign Language', serves: 'P2' },
];

export function ChannelComparison({ blocks }: { blocks: ContentBlock[] }) {
  const [personaId, setPersonaId] = useState<string>(PERSONAS[0]!.id);
  const [blockId, setBlockId] = useState<string>(blocks[0]!.id);
  const [lastResponse, setLastResponse] = useState<LearnerResponse | null>(null);

  const persona = PERSONAS.find((p) => p.id === personaId) ?? PERSONAS[0]!;
  const block = blocks.find((b) => b.id === blockId) ?? blocks[0]!;

  return (
    <main
      id="main"
      tabIndex={-1}
      style={{ padding: 'var(--space-lg, 1.5rem)', maxWidth: '80rem', margin: '0 auto' }}
    >
      <h1 style={{ fontSize: 'var(--type-xxl, 2.25rem)', marginTop: 0 }}>
        One lesson, every learner
      </h1>
      <p style={{ maxWidth: '60ch', color: 'var(--colour-fg-muted)', fontSize: '1.125rem' }}>
        The block below was authored <strong>once</strong>, with no chosen rendering. Everything
        you see is the Modality Router turning that single source into the channels each learner
        can actually use.
      </p>

      <PhrasePicker blocks={blocks} selected={blockId} onSelect={setBlockId} />
      <PersonaSwitcher selected={personaId} onSelect={setPersonaId} />

      <section aria-labelledby="as-rendered" style={{ marginTop: 'var(--space-xl, 2.5rem)' }}>
        <h2 id="as-rendered" style={{ fontSize: 'var(--type-xl, 1.75rem)' }}>
          As {persona.name} receives it
        </h2>
        <p style={{ color: 'var(--colour-fg-muted)', margin: '0 0 var(--space-md, 1rem)' }}>
          {persona.disability} · primary channel plus every supporting channel, together
        </p>

        <div style={panelStyle}>
          {/* Keyed on the profile so React remounts cleanly when the persona
              changes, rather than reconciling two different renderings. */}
          <ProfileProvider key={persona.id} initialProfile={persona.profile}>
            <ModalityRouter block={block} />

            <hr
              style={{
                border: 0,
                borderTop: '1px solid var(--colour-border)',
                margin: 'var(--space-lg, 1.5rem) 0',
              }}
            />

            <ModalityInput
              block={block}
              sessionId="demo-session"
              onResponse={(response) => setLastResponse(response)}
            />
          </ProfileProvider>
        </div>

        {lastResponse && (
          <div style={{ ...panelStyle, marginTop: 'var(--space-md, 1rem)' }}>
            <h3 style={{ margin: '0 0 var(--space-sm, 0.5rem)', fontSize: '1.125rem' }}>
              What the scoring engine receives
            </h3>
            <p style={{ margin: '0 0 var(--space-sm, 0.5rem)', color: 'var(--colour-fg-muted)' }}>
              Typed, tapped as symbols or selected by switch — the shape is identical, which is
              why one scoring engine serves every learner.
            </p>
            <pre style={{ overflowX: 'auto', fontSize: '0.9rem', margin: 0 }}>
              <code>{JSON.stringify(lastResponse, null, 2)}</code>
            </pre>
          </div>
        )}
      </section>

      <section aria-labelledby="all-channels" style={{ marginTop: 'var(--space-xl, 2.5rem)' }}>
        <h2 id="all-channels" style={{ fontSize: 'var(--type-xl, 1.75rem)' }}>
          Every channel, side by side
        </h2>
        <p style={{ color: 'var(--colour-fg-muted)', margin: '0 0 var(--space-md, 1rem)' }}>
          The same block forced through each renderer in turn.
        </p>

        <ul
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(20rem, 1fr))',
            gap: 'var(--space-md, 1rem)',
            listStyle: 'none',
            margin: 0,
            padding: 0,
          }}
        >
          {CHANNELS.map(({ channel, label, serves }) => (
            <li key={channel} style={panelStyle}>
              <h3 style={{ margin: '0 0 var(--space-sm, 0.5rem)', fontSize: '1.125rem' }}>
                {label}{' '}
                <span style={{ fontWeight: 400, color: 'var(--colour-fg-muted)', fontSize: '0.9rem' }}>
                  serves {serves}
                </span>
              </h3>
              <ProfileProvider key={channel} initialProfile={forceProfile(channel)}>
                <ModalityRouter block={block} forceChannel={channel} />
              </ProfileProvider>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="source" style={{ marginTop: 'var(--space-xl, 2.5rem)' }}>
        <h2 id="source" style={{ fontSize: 'var(--type-xl, 1.75rem)' }}>
          The single authored source
        </h2>
        <pre
          style={{
            ...panelStyle,
            overflowX: 'auto',
            fontSize: '0.9rem',
            lineHeight: 1.5,
          }}
        >
          <code>{JSON.stringify(block, null, 2)}</code>
        </pre>
      </section>
    </main>
  );
}

function PhrasePicker({
  blocks,
  selected,
  onSelect,
}: {
  blocks: ContentBlock[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  // Grouped by the category tag the content build stamps on every block, so the
  // 226-phrase bank is navigable rather than one flat list.
  const groups = new Map<string, ContentBlock[]>();
  for (const block of blocks) {
    const category = block.scenario_tags?.[0] ?? 'other';
    groups.set(category, [...(groups.get(category) ?? []), block]);
  }

  return (
    <p style={{ marginTop: 'var(--space-lg, 1.5rem)' }}>
      <label htmlFor="phrase" style={{ display: 'block', fontWeight: 700, marginBottom: '0.5rem' }}>
        Phrase <span style={{ fontWeight: 400, color: 'var(--colour-fg-muted)' }}>
          ({blocks.length} in the Workplace Language Bank)
        </span>
      </label>
      <select
        id="phrase"
        value={selected}
        onChange={(event) => onSelect(event.target.value)}
        style={{
          font: 'inherit',
          minHeight: 'var(--target-min, 44px)',
          width: '100%',
          maxWidth: '44rem',
          padding: 'var(--space-sm, 0.5rem)',
          color: 'var(--colour-fg)',
          background: 'var(--colour-bg)',
          border: '1px solid var(--colour-border)',
          borderRadius: 'var(--radius-md, 8px)',
        }}
      >
        {[...groups.entries()].map(([category, items]) => (
          <optgroup key={category} label={category.replace(/_/g, ' ')}>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.canonical_text}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </p>
  );
}

function PersonaSwitcher({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <fieldset
      style={{
        border: '1px solid var(--colour-border)',
        borderRadius: 'var(--radius-md, 8px)',
        padding: 'var(--space-md, 1rem)',
        marginTop: 'var(--space-lg, 1.5rem)',
      }}
    >
      <legend style={{ padding: '0 var(--space-sm, 0.5rem)', fontWeight: 700 }}>
        View as
      </legend>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm, 0.5rem)' }}>
        {PERSONAS.map((persona) => (
          <label
            key={persona.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              minHeight: 'var(--target-min, 44px)',
              padding: '0 var(--space-md, 1rem)',
              border: '1px solid var(--colour-border)',
              borderRadius: 'var(--radius-md, 8px)',
              background:
                selected === persona.id ? 'var(--colour-accent)' : 'var(--colour-surface)',
              color: selected === persona.id ? 'var(--colour-accent-fg)' : 'var(--colour-fg)',
              cursor: 'pointer',
            }}
          >
            {/* A real radio input, not a styled div: keyboard, screen reader and
                voice control all work for free, and grouping is announced. */}
            <input
              type="radio"
              name="persona"
              value={persona.id}
              checked={selected === persona.id}
              onChange={() => onSelect(persona.id)}
            />
            <span>
              {persona.id} · {persona.name}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** A minimal profile that renders exactly one channel, for the side-by-side grid. */
function forceProfile(channel: OutputChannel): CommunicationAbilityProfile {
  return {
    user_id: `demo-${channel}`,
    version: 1,
    input_channels: ['text'],
    output_channels: [channel],
    text_complexity: channel === 'easy_read' ? 'easy_read' : 'standard',
    speech_status: 'undeclared',
  } as CommunicationAbilityProfile;
}

const panelStyle = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-lg, 14px)',
  padding: 'var(--space-md, 1rem)',
} as const;

export type { Persona };

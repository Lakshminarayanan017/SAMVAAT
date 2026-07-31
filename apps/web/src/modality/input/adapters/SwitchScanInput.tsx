/**
 * Switch-scanning choice input.
 *
 * Primary input for P3 (Arjun), who cannot point. Options are presented as a
 * list, one is highlighted at a time, and a physical switch selects it.
 *
 * The choices come from the block's `target_response.choices` when authored, or
 * are assembled from the correct answer plus its distractors — so a switch user
 * gets the same exercise as everyone else, not a reduced one.
 *
 * Every option remains a real <button>, so this screen is equally operable by
 * mouse, touch, keyboard and voice control. Scanning is an additional way in,
 * never the only way.
 */
import { useMemo, useRef, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';
import { switchScanSettings, useSwitchScan } from '@/a11y/useSwitchScan';

import type { InputAdapterProps } from '../registry';
import { buildResponse } from '../response';

export function SwitchScanInput({
  block,
  profile,
  sessionId,
  onResponse,
  disabled,
}: InputAdapterProps) {
  const [attempts, setAttempts] = useState(1);
  const startedAt = useRef(new Date());
  const announce = useAnnounce();

  const choices = useMemo(() => buildChoices(block), [block]);
  const scan = switchScanSettings(profile);

  const submit = (index: number) => {
    const choice = choices[index];
    if (!choice || disabled) return;

    onResponse(
      buildResponse({
        block,
        profile,
        sessionId,
        inputMode: 'switch',
        text: choice,
        startedAt: startedAt.current,
        attempts,
        // A selection is exact: the learner chose this option, unambiguously.
        confidence: 1,
        raw: { switch_path: [String(index)] },
      }),
    );

    announce('Answer sent');
    setAttempts((n) => n + 1);
    startedAt.current = new Date();
  };

  const { activeIndex, isScanning } = useSwitchScan({
    itemCount: choices.length,
    enabled: scan.enabled && !disabled,
    switchCount: scan.switchCount,
    dwellMs: scan.dwellMs,
    onSelect: submit,
    onFocusChange: (index) => {
      const choice = choices[index];
      if (choice) announce(`${index + 1} of ${choices.length}. ${choice}`);
    },
  });

  const listId = `choices-${block.id}`;

  return (
    <div data-input-mode="switch">
      <h3 id={listId} style={{ fontSize: '1.125rem', margin: '0 0 var(--space-sm, 0.5rem)' }}>
        Choose your answer
      </h3>

      {isScanning && (
        <p style={{ margin: '0 0 var(--space-sm, 0.5rem)', color: 'var(--colour-fg-muted)' }}>
          {scan.switchCount === 2
            ? 'Switch 1 moves the highlight. Switch 2 chooses.'
            : 'The highlight moves on its own. Press your switch to choose.'}
        </p>
      )}

      <ul
        aria-labelledby={listId}
        style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--space-sm, 0.5rem)' }}
      >
        {choices.map((choice, index) => {
          const highlighted = isScanning && index === activeIndex;
          return (
            <li key={choice}>
              <button
                type="button"
                onClick={() => submit(index)}
                disabled={disabled}
                // Communicates the scan highlight to assistive tech, not only
                // to the eye — the highlight is state, not decoration.
                aria-current={highlighted ? 'true' : undefined}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  minHeight: 'var(--target-min, 44px)',
                  padding: 'var(--space-sm, 0.5rem) var(--space-md, 1rem)',
                  borderRadius: 'var(--radius-md, 8px)',
                  background: highlighted ? 'var(--colour-accent)' : 'var(--colour-surface)',
                  color: highlighted ? 'var(--colour-accent-fg)' : 'var(--colour-fg)',
                  // The highlight is carried by a thick border as well as
                  // colour, so it survives a colour-vision difference and a
                  // forced-colours (Windows High Contrast) rendering.
                  border: highlighted
                    ? '4px solid var(--colour-focus)'
                    : '1px solid var(--colour-border)',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  font: 'inherit',
                }}
              >
                {choice}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * The option set: the correct answer plus its authored distractors.
 *
 * Order is stable across renders — deliberately not shuffled. A switch user
 * builds a motor rhythm around option positions, and reshuffling between
 * attempts would penalise exactly the learner this adapter exists for.
 */
function buildChoices(block: InputAdapterProps['block']): string[] {
  const authored = block.interaction.target_response?.choices;
  if (authored?.length) return authored;

  const distractors = block.interaction.distractors ?? [];
  return [block.canonical_text, ...distractors];
}

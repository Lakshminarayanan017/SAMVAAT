/**
 * The four-door screen — the hardest UI in the product.
 *
 * THE PARADOX IT SOLVES
 * ---------------------
 * You cannot ask someone to configure accessibility using an interface that is
 * not yet accessible to them. At this moment we know nothing about the person:
 * whether they can see the screen, hear a sound, read a sentence, or use a
 * mouse. Every later screen is shaped by the answer given here, so this one has
 * to work for all of them at once.
 *
 * HOW
 * ---
 * Four targets, each carrying its meaning four ways simultaneously:
 *
 *   text        for a reader
 *   a symbol    for someone who reads little
 *   speech      for someone who cannot see it (screen reader, or the read-aloud
 *               button for a sighted non-reader)
 *   position    stable and large, so a switch user scanning left to right knows
 *               where they are
 *
 * WHY THERE IS NO AUTOPLAYING AUDIO
 * ---------------------------------
 * Browsers block audio before a user gesture, so an auto-narration would simply
 * fail silently on most devices — the worst possible outcome for the person who
 * needs it. Instead: the page announces itself through the accessibility tree
 * (which screen readers speak immediately, with no gesture required), and a
 * large "Read this aloud" button gives everyone else the same thing on one tap.
 *
 * WHY HIGH CONTRAST AND LARGE TARGETS ARE THE DEFAULT HERE
 * -------------------------------------------------------
 * We do not yet know who this is. The cost of oversized, high-contrast controls
 * to someone who did not need them is nil. The cost of small, low-contrast ones
 * to someone who did is that they never get past this screen.
 */
import { useEffect, useRef, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

export type Door = 'listen' | 'read' | 'sign' | 'pictures';

interface DoorOption {
  id: Door;
  label: string;
  hint: string;
  /** Decorative: the label carries the meaning for assistive tech. */
  symbol: string;
}

const DOORS: DoorOption[] = [
  { id: 'listen', label: 'I will listen', hint: 'You will hear everything spoken', symbol: '🔊' },
  { id: 'read', label: 'I will read', hint: 'You will see everything written', symbol: '📖' },
  { id: 'sign', label: 'I use sign language', hint: 'You will see Indian Sign Language', symbol: '🤟' },
  { id: 'pictures', label: 'I will use pictures', hint: 'Simple words with pictures', symbol: '🖼️' },
];

/** Spoken introduction. Kept short: a long preamble is its own barrier. */
const SPOKEN_INTRO =
  'How would you like to use this app? There are four choices. ' +
  DOORS.map((door, index) => `${index + 1}. ${door.label}. ${door.hint}.`).join(' ') +
  ' You can change this at any time.';

export function FourDoorScreen({ onChoose }: { onChoose: (door: Door) => void }) {
  const announce = useAnnounce();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    // Focus the heading so a screen reader starts here rather than at the top
    // of the document, and announce the choice politely.
    headingRef.current?.focus();
    announce('How would you like to use this app? Four choices.');
  }, [announce]);

  const readAloud = () => {
    // Both are needed, and a browser can have one without the other. Checking
    // only `speechSynthesis` lets the missing constructor throw inside the
    // click handler, which leaves the button looking broken to the one person
    // who most needed it to work.
    if (typeof speechSynthesis === 'undefined' || typeof SpeechSynthesisUtterance === 'undefined') {
      announce('Reading aloud is not available in this browser. The words are on screen.');
      return;
    }

    try {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(SPOKEN_INTRO);
      // Slower than default. Nobody has yet told us they need it faster, and
      // the person most likely to press this button is the one who benefits.
      utterance.rate = 0.85;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);

      setSpeaking(true);
      speechSynthesis.speak(utterance);
    } catch {
      setSpeaking(false);
      announce('Reading aloud did not work. The words are on screen.');
    }
  };

  return (
    <section aria-labelledby="four-door-heading" style={{ maxWidth: '60rem', margin: '0 auto' }}>
      <h1
        id="four-door-heading"
        ref={headingRef}
        tabIndex={-1}
        style={{ fontSize: 'clamp(1.75rem, 5vw, 2.5rem)', marginTop: 0 }}
      >
        How would you like to use this app?
      </h1>

      <p style={{ fontSize: '1.25rem', maxWidth: '40ch' }}>
        Pick the one that suits you best. You can change it at any time.
      </p>

      <p>
        <button
          type="button"
          onClick={readAloud}
          aria-live="off"
          style={{
            minHeight: 'calc(var(--target-min, 44px) * 1.4)',
            padding: '0 var(--space-lg, 1.5rem)',
            fontSize: '1.125rem',
            border: '3px solid var(--colour-fg)',
            borderRadius: 'var(--radius-md, 8px)',
            background: 'var(--colour-bg)',
            color: 'var(--colour-fg)',
            cursor: 'pointer',
            font: 'inherit',
          }}
        >
          {speaking ? 'Reading…' : '🔊 Read this aloud'}
        </button>
      </p>

      <ul
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(16rem, 1fr))',
          gap: 'var(--space-md, 1rem)',
          listStyle: 'none',
          padding: 0,
          marginTop: 'var(--space-lg, 1.5rem)',
        }}
      >
        {DOORS.map((door, index) => (
          <li key={door.id}>
            {/*
              A real <button>: keyboard, switch devices (which emit key presses),
              voice control ("click I will listen") and screen readers all work
              without any further effort. A styled div would need every one of
              those rebuilt by hand, and one of them would be missed.
            */}
            <button
              type="button"
              onClick={() => {
                speechSynthesis?.cancel();
                announce(`${door.label} chosen`);
                onChoose(door.id);
              }}
              style={{
                width: '100%',
                minHeight: '11rem',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '.5rem',
                padding: 'var(--space-md, 1rem)',
                // Thick border, not just colour: this must survive a
                // colour-vision difference and Windows High Contrast mode.
                border: '4px solid var(--colour-fg)',
                borderRadius: 'var(--radius-lg, 14px)',
                background: 'var(--colour-bg)',
                color: 'var(--colour-fg)',
                cursor: 'pointer',
                font: 'inherit',
              }}
            >
              <span aria-hidden="true" style={{ fontSize: '3.5rem', lineHeight: 1 }}>
                {door.symbol}
              </span>
              <span style={{ fontSize: '1.375rem', fontWeight: 700, textAlign: 'center' }}>
                {door.label}
              </span>
              <span style={{ fontSize: '1rem', textAlign: 'center', opacity: 0.85 }}>
                {door.hint}
              </span>
              {/* Read only by assistive tech: gives a switch or screen-reader
                  user their position in the set without cluttering the screen. */}
              <span className="visually-hidden">
                Choice {index + 1} of {DOORS.length}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <p style={{ marginTop: 'var(--space-lg, 1.5rem)', color: 'var(--colour-fg-muted)' }}>
        Not sure? Pick <strong>I will read</strong>. Nothing here is permanent.
      </p>
    </section>
  );
}

export { DOORS, SPOKEN_INTRO };

/**
 * The single live region for the whole application.
 *
 * One announcer, not many. Scattered `aria-live` regions are the classic cause
 * of screen readers either double-announcing or silently dropping messages,
 * because the order in which several regions update is not defined.
 *
 * Usage:
 *   const announce = useAnnounce();
 *   announce('Answer saved');                      // polite
 *   announce('Microphone unavailable', 'assertive'); // interrupts
 *
 * Politeness rule (docs/ACCESSIBILITY.md): `polite` for status, `assertive`
 * only for errors that block progress. Assertive interrupts whatever the
 * learner is currently hearing, which is hostile if it was not important.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

export type Politeness = 'polite' | 'assertive';

type AnnounceFn = (message: string, politeness?: Politeness) => void;

const AnnouncerContext = createContext<AnnounceFn | null>(null);

export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [polite, setPolite] = useState('');
  const [assertive, setAssertive] = useState('');
  const counter = useRef(0);

  const announce = useCallback<AnnounceFn>((message, politeness = 'polite') => {
    if (!message) return;

    // Screen readers ignore a live-region update whose text is unchanged, so an
    // identical repeat message would be silently dropped. Alternating a
    // zero-width space makes the text differ without altering what is read.
    // Written as an escape, never as a literal: an invisible character in source
    // is unreviewable.
    counter.current += 1;
    const text = counter.current % 2 === 0 ? `${message}\u200B` : message;

    if (politeness === 'assertive') setAssertive(text);
    else setPolite(text);
  }, []);

  const value = useMemo(() => announce, [announce]);

  return (
    <AnnouncerContext.Provider value={value}>
      {children}
      <div
        data-testid="announcer-polite"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        style={VISUALLY_HIDDEN}
      >
        {polite}
      </div>
      <div
        data-testid="announcer-assertive"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        style={VISUALLY_HIDDEN}
      >
        {assertive}
      </div>
    </AnnouncerContext.Provider>
  );
}

export function useAnnounce(): AnnounceFn {
  const context = useContext(AnnouncerContext);
  if (!context) {
    throw new Error('useAnnounce must be used inside <AnnouncerProvider>.');
  }
  return context;
}

/**
 * Visually hidden but still read by screen readers.
 *
 * Not `display: none` and not `visibility: hidden` — both remove the element
 * from the accessibility tree, which would defeat the entire purpose.
 */
export const VISUALLY_HIDDEN = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  whiteSpace: 'nowrap',
  border: 0,
} as const;

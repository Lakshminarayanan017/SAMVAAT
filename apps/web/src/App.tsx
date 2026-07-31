/**
 * The application shell.
 *
 * Two views for now: the channel-comparison demo that proves the Modality
 * Router, and the mock interview that is the product's flagship.
 *
 * Deliberately not a router library yet. Two views do not justify one, and the
 * accessibility cost of a client-side router — announcing route changes,
 * managing focus on navigation, keeping the document title in step — is real
 * work that should be done once, properly, when there is enough here to warrant
 * it (M14, with the dashboards).
 *
 * What is done properly already: the view switcher is a real tablist, focus
 * moves to the new view's heading on change, and the change is announced.
 */
import { useEffect, useRef, useState } from 'react';
import type { ContentBlock } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { ProfileProvider } from '@/a11y/ProfileProvider';
import { ChannelComparison } from '@/features/channel-comparison/ChannelComparison';
import { PERSONAS } from '@/features/channel-comparison/personas';
import { InterviewSession } from '@/features/interview/InterviewSession';

type View = 'router' | 'interview';

const VIEWS: { id: View; label: string }[] = [
  { id: 'router', label: 'One lesson, every learner' },
  { id: 'interview', label: 'Practise an interview' },
];

export function App({ blocks }: { blocks: ContentBlock[] }) {
  const [view, setView] = useState<View>('router');
  const announce = useAnnounce();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    // Move focus into the new view and say what happened. Without this a
    // screen-reader user is left at the tab they just pressed, with no idea the
    // page beneath it changed.
    mainRef.current?.focus();
    announce(`${VIEWS.find((v) => v.id === view)?.label} view`);
  }, [view, announce]);

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to main content
      </a>

      <header
        style={{
          borderBottom: '1px solid var(--colour-border)',
          padding: 'var(--space-md, 1rem) var(--space-lg, 1.5rem)',
        }}
      >
        <p style={{ margin: 0, fontWeight: 700, fontSize: '1.25rem' }}>SAMVAAD</p>

        <div role="tablist" aria-label="Views" style={{ display: 'flex', gap: '.5rem', marginTop: '.75rem' }}>
          {VIEWS.map((item) => (
            <button
              key={item.id}
              role="tab"
              type="button"
              aria-selected={view === item.id}
              aria-controls="main"
              onClick={() => setView(item.id)}
              style={{
                minHeight: 'var(--target-min, 44px)',
                padding: '0 1rem',
                border: '1px solid var(--colour-border)',
                borderRadius: 8,
                background: view === item.id ? 'var(--colour-accent)' : 'var(--colour-surface)',
                color: view === item.id ? 'var(--colour-accent-fg)' : 'var(--colour-fg)',
                cursor: 'pointer',
                font: 'inherit',
                fontWeight: view === item.id ? 700 : 400,
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <main
        id="main"
        ref={mainRef}
        tabIndex={-1}
        style={{ padding: 'var(--space-lg, 1.5rem)', maxWidth: '80rem', margin: '0 auto' }}
      >
        {view === 'router' ? (
          <ChannelComparison blocks={blocks} embedded />
        ) : (
          // Keyed on the profile so switching persona remounts cleanly rather
          // than reconciling an interview across two different renderings.
          <ProfileProvider key="interview" initialProfile={PERSONAS[0]!.profile}>
            <InterviewSession />
          </ProfileProvider>
        )}
      </main>
    </>
  );
}

/**
 * The application shell.
 *
 * Boots a session, and if the learner has not been through onboarding, shows
 * the four-door screen before anything else. Nothing is rendered in a modality
 * until the learner has told us which one they can use — which is the whole
 * point of building the router first.
 *
 * Deliberately not a router library yet. Three views do not justify one, and the
 * accessibility cost of a client-side router — announcing route changes,
 * managing focus, keeping the document title in step — is real work that should
 * be done once, properly, when there is enough here to warrant it (M14).
 *
 * What is done properly already: the view switcher is a real tablist, focus
 * moves to the new view on change, and the change is announced.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { CommunicationAbilityProfile, ContentBlock } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { DEFAULT_PROFILE, ProfileProvider } from '@/a11y/ProfileProvider';
import { ChannelComparison } from '@/features/channel-comparison/ChannelComparison';
import { InterviewSession } from '@/features/interview/InterviewSession';
import { OnboardingFlow } from '@/features/onboarding/OnboardingFlow';
import { PracticeSession } from '@/features/practice/PracticeSession';
import { ProgressPanel } from '@/features/progress/ProgressPanel';
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { authHeaders, startSession, type Session } from '@/services/session';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

type View = 'practice' | 'interview' | 'progress' | 'trainer' | 'router';

const LEARNER_VIEWS: { id: View; label: string }[] = [
  { id: 'practice', label: 'Practise phrases' },
  { id: 'interview', label: 'Practise an interview' },
  { id: 'progress', label: 'My progress' },
  { id: 'router', label: 'How this works' },
];

//: Only rendered for a trainer token. The API refuses it regardless of what the
//: client shows, so this is presentation rather than a security boundary.
const TRAINER_VIEW: { id: View; label: string } = { id: 'trainer', label: 'My learners' };

type Boot = 'starting' | 'onboarding' | 'ready' | 'offline';

export function App({ blocks }: { blocks: ContentBlock[] }) {
  const announce = useAnnounce();

  const [boot, setBoot] = useState<Boot>('starting');
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<CommunicationAbilityProfile>(DEFAULT_PROFILE);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [view, setView] = useState<View>('practice');

  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  // ── boot ───────────────────────────────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const started = await startSession();
      if (cancelled) return;

      if (!started) {
        setBoot('offline');
        return;
      }

      setSession(started);

      if (started.needsOnboarding) {
        setBoot('onboarding');
        return;
      }

      const response = await fetch(`${BASE_URL}/profile`, {
        headers: authHeaders(started.token),
      }).catch(() => null);

      if (!cancelled && response?.ok) {
        setProfile((await response.json()) as CommunicationAbilityProfile);
      }
      if (!cancelled) setBoot('ready');
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const completeOnboarding = useCallback(
    async (partial: Partial<CommunicationAbilityProfile>) => {
      if (!session) return;

      setSaving(true);
      setSaveError(null);

      const response = await fetch(`${BASE_URL}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(session.token) },
        body: JSON.stringify(partial),
      }).catch(() => null);

      setSaving(false);

      if (!response?.ok) {
        // The learner has just told us how they need to be spoken to. Losing
        // that silently and dropping them into a default modality would be
        // worse than any error message.
        setSaveError('We could not save your choices. Please try that once more.');
        return;
      }

      setProfile((await response.json()) as CommunicationAbilityProfile);
      setBoot('ready');
      announce('All set. Welcome.');
    },
    [announce, session],
  );

  // ── view changes ───────────────────────────────────────────────────────────

  const views = session?.isTrainer ? [...LEARNER_VIEWS, TRAINER_VIEW] : LEARNER_VIEWS;

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    mainRef.current?.focus();
    announce(`${views.find((item) => item.id === view)?.label} view`);
  }, [view, announce, views]);

  // ── states before the app proper ───────────────────────────────────────────

  if (boot === 'starting') {
    return (
      <main style={shell}>
        <p role="status">Getting things ready…</p>
      </main>
    );
  }

  if (boot === 'offline') {
    return (
      <main style={shell}>
        <h1>We cannot reach the app right now</h1>
        <p style={{ maxWidth: '50ch' }}>
          This is our problem, not yours. Please try again in a few minutes — nothing you have
          done has been lost.
        </p>
        <button type="button" onClick={() => window.location.reload()} style={primaryButton}>
          Try again
        </button>
      </main>
    );
  }

  if (boot === 'onboarding') {
    return (
      <main id="main" style={shell}>
        <OnboardingFlow onComplete={completeOnboarding} saving={saving} error={saveError} />
      </main>
    );
  }

  // ── the app ────────────────────────────────────────────────────────────────

  return (
    <ProfileProvider initialProfile={profile}>
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

        <div
          role="tablist"
          aria-label="Views"
          style={{ display: 'flex', gap: '.5rem', marginTop: '.75rem', flexWrap: 'wrap' }}
        >
          {views.map((item) => (
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
        {view === 'practice' && session && (
          <PracticeSession token={session.token} blocks={blocks} />
        )}
        {view === 'interview' && <InterviewSession userId={session?.userId ?? 'guest'} />}
        {view === 'progress' && session && <ProgressPanel token={session.token} />}
        {view === 'trainer' && session && <TrainerDashboard token={session.token} />}
        {view === 'router' && <ChannelComparison blocks={blocks} embedded />}
      </main>
    </ProfileProvider>
  );
}

const shell = {
  padding: 'var(--space-xl, 2.5rem) var(--space-lg, 1.5rem)',
  maxWidth: '70rem',
  margin: '0 auto',
} as const;

const primaryButton = {
  minHeight: 'var(--target-min, 44px)',
  padding: '0 var(--space-lg, 1.5rem)',
  border: '2px solid var(--colour-border)',
  borderRadius: 8,
  background: 'var(--colour-accent)',
  color: 'var(--colour-accent-fg)',
  cursor: 'pointer',
  font: 'inherit',
} as const;

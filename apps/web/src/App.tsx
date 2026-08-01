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
import { InstitutionDashboard } from '@/features/institution/InstitutionDashboard';
import { InterviewSession } from '@/features/interview/InterviewSession';
import { OnboardingFlow } from '@/features/onboarding/OnboardingFlow';
import { PracticeSession } from '@/features/practice/PracticeSession';
import { ProgressPanel } from '@/features/progress/ProgressPanel';
import { StoryChooser } from '@/features/stories/StoryChooser';
import { TrainerDashboard } from '@/features/trainer/TrainerDashboard';
import { getContent } from '@/offline/content';
import { outboxSize } from '@/offline/db';
import { startSync } from '@/offline/sync';
import { authHeaders, startSession, type Session } from '@/services/session';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

type View =
  | 'practice'
  | 'interview'
  | 'stories'
  | 'progress'
  | 'trainer'
  | 'institution'
  | 'router';

const LEARNER_VIEWS: { id: View; label: string }[] = [
  { id: 'practice', label: 'Practise phrases' },
  { id: 'interview', label: 'Practise an interview' },
  { id: 'stories', label: 'Understand a situation' },
  { id: 'progress', label: 'My progress' },
  { id: 'router', label: 'How this works' },
];

//: Only rendered for a trainer token. The API refuses it regardless of what the
//: client shows, so this is presentation rather than a security boundary.
const TRAINER_VIEW: { id: View; label: string } = { id: 'trainer', label: 'My learners' };

//: Likewise. An institution sees anonymised aggregates and nothing else — a
//: different tab from the trainer's, because neither role implies the other.
const INSTITUTION_VIEW: { id: View; label: string } = {
  id: 'institution',
  label: 'Cohort report',
};

type Boot = 'starting' | 'onboarding' | 'ready' | 'offline';

export function App() {
  const announce = useAnnounce();

  // The phrase bank is fetched and cached rather than bundled (M15). A
  // learner on a metered connection should not pay for 226 blocks of
  // JavaScript before seeing a single lesson.
  const [blocks, setBlocks] = useState<ContentBlock[]>([]);
  const [contentSource, setContentSource] = useState<'cache' | 'network' | 'unavailable'>(
    'network',
  );
  const [queued, setQueued] = useState(0);

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

      const content = await getContent();
      if (cancelled) return;
      setBlocks(content.blocks);
      setContentSource(content.source);

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

  // ── offline sync ───────────────────────────────────────────────────────────

  useEffect(() => {
    if (!session) return;

    const refresh = () => void outboxSize().then(setQueued);
    refresh();

    // Replays anything the learner did offline, oldest first. Nothing leaves
    // the outbox until the server confirms it.
    const stop = startSync(session.token, (result) => {
      refresh();
      if (result.sent > 0) {
        announce(`${result.sent} saved answer${result.sent === 1 ? '' : 's'} sent.`);
      }
    });

    return stop;
  }, [session, announce]);

  // ── view changes ───────────────────────────────────────────────────────────

  const views = [
    ...LEARNER_VIEWS,
    ...(session?.isTrainer ? [TRAINER_VIEW] : []),
    ...(session?.isInstitution ? [INSTITUTION_VIEW] : []),
  ];

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

        <OfflineNotice source={contentSource} queued={queued} />

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
        {view === 'stories' && session && <StoryChooser token={session.token} />}
        {view === 'progress' && session && <ProgressPanel token={session.token} />}
        {view === 'trainer' && session && <TrainerDashboard token={session.token} />}
        {view === 'institution' && session && <InstitutionDashboard token={session.token} />}
        {view === 'router' && <ChannelComparison blocks={blocks} embedded />}
      </main>
    </ProfileProvider>
  );
}

/**
 * What is happening with the network, in plain words.
 *
 * Only appears when there is something to say. A permanent "you are online"
 * badge is noise; a learner needs to know when their work is waiting, and
 * nothing else.
 */
function OfflineNotice({
  source,
  queued,
}: {
  source: 'cache' | 'network' | 'unavailable';
  queued: number;
}) {
  if (source === 'network' && queued === 0) return null;

  const message =
    source === 'unavailable'
      ? 'We could not load your lessons. Check your connection and try again.'
      : queued > 0
        ? `Working offline. ${queued} answer${queued === 1 ? '' : 's'} saved here, ` +
          'and they will be sent when you are back online.'
        : 'Working from your saved lessons.';

  return (
    <p
      role="status"
      data-testid="offline-notice"
      style={{
        margin: '.5rem 0 0',
        fontSize: '.95rem',
        color: 'var(--colour-fg-muted)',
      }}
    >
      {message}
    </p>
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

/**
 * The app shell — boot, then routes.
 *
 * Boot is deliberately still linear and still outside the router: session,
 * content, onboarding gate. Those are not navigable states. A learner part-way
 * through the four-door screen must not be able to reach `/me/settings` by
 * pressing Back, because the settings screen renders in a modality they have
 * not chosen yet.
 *
 * The navigation is a real `<nav>` with links, not a tablist with buttons. The
 * old tab bar used `role="tablist"`, which was correct when the content swapped
 * in place; with real URLs, a tab that is actually a link announcing itself as
 * a tab is a lie a screen reader user has to see through.
 */
import { Suspense, useCallback, useEffect, useState } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import type { CommunicationAbilityProfile, ContentBlock } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { DEFAULT_PROFILE, ProfileProvider } from '@/a11y/ProfileProvider';
import { OnboardingFlow } from '@/features/onboarding/OnboardingFlow';
import { getContent } from '@/offline/content';
import { AppRoute } from '@/routes/AppRoute';
import { ROUTES, navigationFor } from '@/routes/routes';
import { SessionProvider, useSession, type ContentSource } from '@/services/SessionProvider';
import { authHeaders, startSession, type Session } from '@/services/session';
import { Button, Card, ErrorState, Skeleton, Stack, Text } from '@/ui';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

type Boot = 'starting' | 'onboarding' | 'ready' | 'offline';

export function AppShell() {
  const announce = useAnnounce();

  const [boot, setBoot] = useState<Boot>('starting');
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<CommunicationAbilityProfile>(DEFAULT_PROFILE);
  const [blocks, setBlocks] = useState<ContentBlock[]>([]);
  const [contentSource, setContentSource] = useState<ContentSource>('network');
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

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

      // Profile and flags together. Sequentially they would add a round trip
      // to every boot on a connection where round trips are the expensive part.
      const [profileResponse, flagsResponse] = await Promise.all([
        fetch(`${BASE_URL}/profile`, { headers: authHeaders(started.token) }).catch(() => null),
        fetch(`${BASE_URL}/flags`, { headers: authHeaders(started.token) }).catch(() => null),
      ]);
      if (cancelled) return;

      if (profileResponse?.ok) {
        setProfile((await profileResponse.json()) as CommunicationAbilityProfile);
      }
      // Flags failing to load is not an error the learner should see. Every
      // flag's off-state is the current behaviour, so an empty map is a
      // completely usable app.
      if (flagsResponse?.ok) {
        const body = (await flagsResponse.json()) as { flags?: Record<string, boolean> };
        setFlags(body.flags ?? {});
      }

      setBoot('ready');
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

  if (boot === 'starting') {
    return (
      <main style={{ padding: 'var(--space-lg, 1.5rem)', maxInlineSize: '40rem', margin: '0 auto' }}>
        <Skeleton label="Getting things ready" height="3rem" />
      </main>
    );
  }

  if (boot === 'offline') {
    return (
      <main style={{ padding: 'var(--space-lg, 1.5rem)', maxInlineSize: '40rem', margin: '0 auto' }}>
        <ErrorState
          title="We cannot reach the app right now"
          body="This is our problem, not yours. Please try again in a few minutes — nothing you have done has been lost."
          action={{ label: 'Try again', onClick: () => window.location.reload() }}
        />
      </main>
    );
  }

  if (boot === 'onboarding') {
    return (
      <main id="main" style={{ padding: 'var(--space-lg, 1.5rem)' }}>
        <OnboardingFlow onComplete={completeOnboarding} saving={saving} error={saveError} />
      </main>
    );
  }

  if (!session) return null;

  return (
    <ProfileProvider initialProfile={profile}>
      <SessionProvider
          session={session}
          blocks={blocks}
          contentSource={contentSource}
          flags={flags}
        >
        <BrowserRouter>
          <Chrome session={session} contentSource={contentSource} />
        </BrowserRouter>
      </SessionProvider>
    </ProfileProvider>
  );
}

/**
 * Navigation plus the routed content.
 *
 * Inside `<BrowserRouter>` because `NavLink` needs the router context, and
 * because whether the chrome is shown at all is a per-route decision.
 */
function Chrome({ session, contentSource }: { session: Session; contentSource: ContentSource }) {
  // The count the sync loop keeps up to date, rather than a second poller
  // disagreeing with the first.
  const { queued } = useSession();
  const nav = navigationFor({
    isTrainer: session.isTrainer,
    isInstitution: session.isInstitution,
  });

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to main content
      </a>

      <header
        data-app-chrome
        style={{
          borderBlockEnd: '1px solid var(--border-subtle)',
          padding: 'var(--space-md, 1rem) var(--space-lg, 1.5rem)',
        }}
      >
        <Text variant="heading" as="p" style={{ marginBlockEnd: '0.5rem' }}>
          SAMVAAD
        </Text>

        <OfflineNotice source={contentSource} queued={queued} />

        {/* A real nav with links. The old tab bar announced itself as a tablist,
            which was true when content swapped in place and is a lie now that
            these are URLs. */}
        <nav aria-label="Main">
          <Stack as="ul" direction="horizontal" gap="sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {nav.map((route) => (
              <li key={route.path}>
                <NavLink
                  to={route.path}
                  data-ui="button"
                  // `end` so "/" is only current at "/", rather than matching
                  // every route beneath it.
                  end={route.path === '/'}
                  style={({ isActive }) => ({
                    display: 'inline-flex',
                    alignItems: 'center',
                    minBlockSize: 'var(--target-min, 44px)',
                    paddingInline: '1rem',
                    borderRadius: 'var(--radius-md, 8px)',
                    border: '1px solid var(--border-strong)',
                    background: isActive ? 'var(--interactive-rest)' : 'var(--surface-raised)',
                    color: isActive ? 'var(--text-on-interactive)' : 'var(--text-primary)',
                    fontWeight: isActive ? 700 : 400,
                    textDecoration: 'none',
                  })}
                  // NavLink sets aria-current="page" itself, which is what
                  // actually tells a screen reader which page this is. Colour
                  // and weight say the same thing to everyone else.
                >
                  {route.navLabel}
                </NavLink>
              </li>
            ))}
          </Stack>
        </nav>
      </header>

      <Suspense
        fallback={
          <AppRoute title="Loading">
            <Skeleton label="Loading this page" height="6rem" />
          </AppRoute>
        }
      >
        <Routes>
          {ROUTES.map(({ path, component: Component }) => (
            <Route key={path} path={path} element={<Component />} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </>
  );
}

function NotFound() {
  return (
    <AppRoute title="We could not find that page">
      <Card padding="lg">
        <Stack gap="sm">
          <Text variant="title" as="h1">
            We could not find that page
          </Text>
          <Text variant="body" measure>
            The link may be out of date. Everything you have done is still here.
          </Text>
          <div>
            <Button variant="primary" onRaised onClick={() => window.location.assign('/')}>
              Go to my map
            </Button>
          </div>
        </Stack>
      </Card>
    </AppRoute>
  );
}

/**
 * What is happening with the network, in plain words.
 *
 * Only appears when there is something to say. A permanent "you are online"
 * badge is noise; a learner needs to know when their work is waiting.
 */
function OfflineNotice({ source, queued }: { source: ContentSource; queued: number }) {
  if (source === 'network' && queued === 0) return null;

  return (
    <Text variant="caption" tone="secondary" as="p" style={{ marginBlockEnd: '0.5rem' }}>
      {source === 'unavailable'
        ? 'We could not load the phrases. Please try again when you are back online.'
        : source === 'cache'
          ? 'Working offline. Everything you do is saved and will be sent when you reconnect.'
          : null}
      {queued > 0 &&
        ` ${queued} answer${queued === 1 ? '' : 's'} waiting to be sent.`}
    </Text>
  );
}

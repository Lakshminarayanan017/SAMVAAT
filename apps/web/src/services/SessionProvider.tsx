/**
 * Session and content, shared with every route.
 *
 * Before the router, `App.tsx` held the session and passed `token` down to each
 * screen as a prop. That worked because there was exactly one place rendering
 * screens. With routes, the alternative to a context is threading the token
 * through the route table into every lazily-loaded component, which is both
 * noisy and easy to get wrong in the direction that matters — a screen that
 * silently receives `undefined` makes an unauthenticated request and shows an
 * error the learner cannot act on.
 *
 * Deliberately not a general-purpose store. It holds the three things every
 * route legitimately needs — who the learner is, the phrase bank, and whether
 * anything is queued offline — and nothing else.
 */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { ContentBlock } from '@samvaad/contracts';

import { outboxSize } from '@/offline/db';
import { startSync } from '@/offline/sync';
import { useAnnounce } from '@/a11y/Announcer';
import type { Session } from '@/services/session';

export type ContentSource = 'cache' | 'network' | 'unavailable';

export interface SessionValue {
  session: Session;
  blocks: ContentBlock[];
  contentSource: ContentSource;
  /** How many answers are waiting to be sent. Zero when online and caught up. */
  queued: number;
  /**
   * Feature flags for this learner, fetched once at boot.
   *
   * An unknown flag reads as off, matching the server. A flag that flips
   * mid-session would change the interface underneath somebody, which for a
   * learner with a cognitive disability is the app becoming a different app
   * while they are using it — so this is never refetched.
   */
  flags: Readonly<Record<string, boolean>>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({
  session,
  blocks,
  contentSource,
  flags = {},
  children,
}: {
  session: Session;
  blocks: ContentBlock[];
  contentSource: ContentSource;
  flags?: Record<string, boolean>;
  children: ReactNode;
}) {
  const announce = useAnnounce();
  const [queued, setQueued] = useState(0);

  useEffect(() => {
    const refresh = () => void outboxSize().then(setQueued);
    refresh();

    // Replays anything done offline, oldest first. Nothing leaves the outbox
    // until the server confirms it.
    return startSync(session.token, (result) => {
      refresh();
      if (result.sent > 0) {
        announce(`${result.sent} saved answer${result.sent === 1 ? '' : 's'} sent.`);
      }
    });
  }, [session.token, announce]);

  const value = useMemo(
    () => ({ session, blocks, contentSource, queued, flags }),
    [session, blocks, contentSource, queued, flags],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/**
 * The session, for a route that requires one.
 *
 * Throws rather than returning null. Every route inside the shell is rendered
 * only after boot has produced a session, so a missing one is a wiring mistake
 * — and a screen that quietly renders with no token produces a 401 the learner
 * is shown as though it were their problem.
 */
export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error(
      'useSession must be used inside <SessionProvider>. Every route renders after boot, ' +
        'so reaching this means a screen was mounted outside the app shell.',
    );
  }
  return value;
}

/**
 * Is this feature on for this learner?
 *
 * Defaults to off for an unknown name, matching the server. A typo must not
 * enable an unfinished surface, and it must not throw either — a flag lookup is
 * not a place to take the screen down.
 */
export function useFlag(name: string): boolean {
  const { flags } = useSession();
  return flags[name] ?? false;
}

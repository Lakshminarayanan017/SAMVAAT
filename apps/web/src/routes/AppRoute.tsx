/**
 * The accessible route contract (Blueprint F2, ADR-0014).
 *
 * THIS IS THE HIGHEST-RISK COMPONENT IN THE REDESIGN.
 *
 * A tab bar that swaps content in place is, accessibility-wise, quite easy to
 * get right: the old App.tsx moved focus and announced on every change, in one
 * place, because there was only one place. A client-side router removes that
 * guarantee — each route becomes an independent opportunity to forget, and
 * forgetting is silent. The learner simply finds that focus is still on the
 * link they pressed, at the top of a document whose content has entirely
 * changed, with nothing announced.
 *
 * For a screen-reader user that means re-reading the page to work out what
 * happened. For a switch user it means restarting the scan from the beginning
 * of the document on every navigation, which is a real and repeated cost.
 *
 * So the safe path is the ONLY path: every route renders through `<AppRoute>`,
 * which does all three things a navigation must do —
 *
 *   1. moves focus to the new `<main>`,
 *   2. announces the destination,
 *   3. updates `document.title`,
 *
 * — and `tests/routes/contract.test.tsx` walks the real route table and fails
 * on any route that does not. A route added without the wrapper does not
 * silently regress; it fails CI.
 *
 * WHY FOCUS GOES TO <main> AND NOT TO THE HEADING
 * -----------------------------------------------
 * Focusing the `<h1>` reads the heading and then leaves the user *after* it, so
 * Shift+Tab lands them outside the content they just arrived at. Focusing the
 * container puts them at the start of the new content with everything ahead of
 * them, which is what "you have arrived here" should mean.
 *
 * `tabIndex={-1}` makes it programmatically focusable without adding it to the
 * tab order — a `<main>` a keyboard user has to tab *through* is an obstacle,
 * not an affordance.
 */
import { useEffect, useRef, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

import { useAnnounce } from '@/a11y/Announcer';

export interface AppRouteProps {
  /**
   * What this surface is, in the learner's words.
   *
   * Used for all three of the title, the announcement and the accessible name
   * of `<main>`, so they cannot drift apart into three different descriptions
   * of the same place.
   */
  title: string;
  /**
   * Full-screen surfaces hide the app chrome entirely (Blueprint §5.3).
   *
   * A learner mid-mission should see the mission and nothing else. This is the
   * structural half of "not a dashboard" — navigation that stays on screen
   * during a task is navigation inviting the learner to leave it.
   */
  chromeless?: boolean;
  children: ReactNode;
}

const TITLE_SUFFIX = 'SAMVAAD';

export function AppRoute({ title, chromeless = false, children }: AppRouteProps) {
  const announce = useAnnounce();
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);

  // Skips the announcement on first paint. Announcing the landing page to
  // somebody who has just opened the app tells them where they already know
  // they are, and it competes with the screen reader's own page-load reading.
  const isFirstRender = useRef(true);

  useEffect(() => {
    document.title = `${title} · ${TITLE_SUFFIX}`;
  }, [title]);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    mainRef.current?.focus();
    announce(title);
    // `location.key` rather than `pathname`: navigating to the route you are
    // already on (pressing "Home" from home) is still a navigation the learner
    // performed, and silence would read as the button being broken.
  }, [location.key, title, announce]);

  return (
    <main
      ref={mainRef}
      tabIndex={-1}
      aria-label={title}
      data-route={location.pathname}
      data-chromeless={chromeless ? 'true' : undefined}
      style={{
        // Focus lands here on every navigation, and a visible ring around the
        // whole page is alarming rather than useful — the announcement is what
        // carries the information. Individual controls keep their rings.
        outline: 'none',
        padding: chromeless ? 0 : 'var(--space-md, 1rem)',
        maxInlineSize: chromeless ? undefined : '80rem',
        marginInline: chromeless ? undefined : 'auto',
        inlineSize: '100%',
      }}
    >
      {children}
    </main>
  );
}

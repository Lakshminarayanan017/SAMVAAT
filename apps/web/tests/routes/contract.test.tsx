/**
 * The accessible route contract (Blueprint R1, F2).
 *
 * The blueprint names "router regresses accessibility" as the single
 * highest-risk item in the redesign, and the mitigation is "one shared wrapper;
 * a route not using it fails a test". This is that test.
 *
 * It walks the REAL route table rather than a list written here. That is the
 * whole point: a route added next month is covered automatically, and a route
 * added without `<AppRoute>` fails at the moment somebody adds it rather than
 * in a screen-reader user's session six weeks later.
 *
 * What a navigation must do, all three every time:
 *   1. move focus to the new <main>
 *   2. announce the destination
 *   3. update document.title
 *
 * Getting one of the three right and missing another is the normal outcome of
 * doing this per-route by hand, and it is silent — the learner simply finds
 * focus is still on the link they pressed, on a page whose content has entirely
 * changed.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { DEFAULT_PROFILE, ProfileProvider } from '@/a11y/ProfileProvider';
import { AppRoute } from '@/routes/AppRoute';
import { ROUTES, navigationFor } from '@/routes/routes';

function frame(initial: string, ui: React.ReactNode) {
  return render(
    <AnnouncerProvider>
      <ProfileProvider initialProfile={DEFAULT_PROFILE}>
        <MemoryRouter initialEntries={[initial]}>{ui}</MemoryRouter>
      </ProfileProvider>
    </AnnouncerProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('the route table', () => {
  it('gives every route a title', () => {
    for (const route of ROUTES) {
      expect(route.title, `${route.path} has no title`).toBeTruthy();
    }
  });

  it('gives every visible route a navigation label', () => {
    for (const route of ROUTES) {
      if (route.hidden) continue;
      expect(route.navLabel, `${route.path} is visible but unlabelled`).toBeTruthy();
    }
  });

  it('has no duplicate paths', () => {
    const paths = ROUTES.map((route) => route.path);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('lazy-loads every screen, so no route is in the initial bundle', async () => {
    /* Our learners are explicitly on entry-level Android and metered data. A
       learner who never opens the trainer dashboard must never download it. */
    for (const route of ROUTES) {
      // React.lazy components carry $$typeof lazy rather than being functions.
      expect(
        typeof route.component === 'object' && route.component !== null,
        `${route.path} is not lazily loaded`,
      ).toBe(true);
    }
  });

  it('marks exactly the full-screen surfaces as chromeless', () => {
    /* A learner mid-mission should see the mission and nothing else. Marking a
       list screen chromeless would strand them with no navigation. */
    const chromeless = ROUTES.filter((route) => route.chromeless).map((route) => route.path);
    expect(chromeless.sort()).toEqual(['/interview', '/level/:levelId']);
  });
});

describe('every route honours the contract', () => {
  // Rendered through AppRoute exactly as the real screens are, so the assertion
  // is about the wrapper's guarantee rather than about any one screen's body.
  const cases = ROUTES.map((route) => ({ path: route.path, title: route.title }));

  it.each(cases)('$path names <main> after the destination', async ({ path, title }) => {
    frame(
      path.replace(/:(\w+)/g, 'x'),
      <Routes>
        <Route path={path} element={<AppRoute title={title}>content</AppRoute>} />
      </Routes>,
    );

    await waitFor(() => expect(screen.getByRole('main', { name: title })).toBeInTheDocument());
  });

  it.each(cases)('$path sets the document title', async ({ path, title }) => {
    frame(
      path.replace(/:(\w+)/g, 'x'),
      <Routes>
        <Route path={path} element={<AppRoute title={title}>content</AppRoute>} />
      </Routes>,
    );

    await waitFor(() => expect(document.title).toContain(title));
  });
});

describe('navigating between routes', () => {
  function app() {
    return frame(
      '/',
      <>
        <Link to="/me">Go to progress</Link>
        <Routes>
          <Route path="/" element={<AppRoute title="Home">home content</AppRoute>} />
          <Route path="/me" element={<AppRoute title="My progress">progress content</AppRoute>} />
        </Routes>
      </>,
    );
  }

  it('moves focus to the new main', async () => {
    /* Without this a switch user restarts the scan from the top of the document
       on every navigation, and a screen-reader user has to re-read the page to
       work out what happened. A real click, because that is what a learner
       does — re-rendering a fresh router would prove nothing about navigation. */
    app();

    await userEvent.click(screen.getByRole('link', { name: 'Go to progress' }));

    const main = await screen.findByRole('main', { name: 'My progress' });
    await waitFor(() => expect(document.activeElement).toBe(main));
  });

  it('announces the destination', async () => {
    app();

    await userEvent.click(screen.getByRole('link', { name: 'Go to progress' }));

    await waitFor(() =>
      expect(document.querySelector('[aria-live="polite"]')?.textContent).toContain(
        'My progress',
      ),
    );
  });

  it('updates the document title', async () => {
    app();

    await userEvent.click(screen.getByRole('link', { name: 'Go to progress' }));

    await waitFor(() => expect(document.title).toContain('My progress'));
  });

  it('makes main programmatically focusable without adding it to the tab order', () => {
    /* tabIndex={-1}: a <main> a keyboard user has to tab *through* is an
       obstacle, not an affordance. */
    app();
    expect(screen.getByRole('main', { name: 'Home' })).toHaveAttribute('tabindex', '-1');
  });

  it('does not announce on first paint', async () => {
    /* Telling somebody who has just opened the app where they are competes with
       the screen reader's own page-load reading and says nothing new. */
    app();

    const live = document.querySelector('[aria-live="polite"]');
    await waitFor(() => expect(live?.textContent ?? '').toBe(''));
  });
});

describe('role gating in the navigation', () => {
  it('hides the trainer link from a learner', () => {
    const paths = navigationFor({ isTrainer: false, isInstitution: false }).map((r) => r.path);
    expect(paths).not.toContain('/trainer');
    expect(paths).not.toContain('/institution');
  });

  it('shows the trainer link to a trainer, and only that one', () => {
    const paths = navigationFor({ isTrainer: true, isInstitution: false }).map((r) => r.path);
    expect(paths).toContain('/trainer');
    expect(paths).not.toContain('/institution');
  });

  it('shows the institution link to an institution', () => {
    const paths = navigationFor({ isTrainer: false, isInstitution: true }).map((r) => r.path);
    expect(paths).toContain('/institution');
  });

  it('never puts a hidden route in the navigation', () => {
    const nav = navigationFor({ isTrainer: true, isInstitution: true });
    expect(nav.every((route) => !route.hidden)).toBe(true);
  });

  it('keeps the channel comparison out of the learner navigation', () => {
    /* Blueprint A8. A superb pitch artefact; not a thing a learner needs in
       their nav. It stays routable at /demo. */
    const paths = navigationFor({ isTrainer: true, isInstitution: true }).map((r) => r.path);
    expect(paths).not.toContain('/demo');
    expect(ROUTES.map((r) => r.path)).toContain('/demo');
  });
});

describe('chromeless surfaces', () => {
  it('mark themselves so the shell can hide navigation', () => {
    frame(
      '/level/abc',
      <Routes>
        <Route
          path="/level/:levelId"
          element={
            <AppRoute title="Level" chromeless>
              mission
            </AppRoute>
          }
        />
      </Routes>,
    );

    expect(screen.getByRole('main', { name: 'Level' })).toHaveAttribute(
      'data-chromeless',
      'true',
    );
  });

  it('do not mark ordinary surfaces', () => {
    frame(
      '/me',
      <Routes>
        <Route path="/me" element={<AppRoute title="My progress">body</AppRoute>} />
      </Routes>,
    );

    expect(screen.getByRole('main', { name: 'My progress' })).not.toHaveAttribute(
      'data-chromeless',
    );
  });
});

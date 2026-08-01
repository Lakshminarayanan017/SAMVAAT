# ADR-0008 · A client router, and one accessible route contract

**Status:** Accepted
**Date:** 2026-08-01
**Blueprint:** F2, R1, §5.3 · listed in Appendix B as ADR-0014; numbered 0008 to follow the
existing sequence.

## Context

Until now the client had no router. `App.tsx` held a `view` string in state and swapped
content in place behind a `role="tablist"`. That was a defensible decision at six tabs and
`docs/STATUS.md` recorded it honestly, with the trigger named: *"when a surface needs a
shareable URL. A trainer emailing a learner 'open this page' is the trigger."*

The redesign is that trigger, twice over:

1. **Ten worlds × five chapters × fifty levels does not fit in a tab bar.** A learner needs
   to be sent to World 5, Chapter 2, and "open the app, press Home, scroll" is not a link.
2. **Code splitting needs routes.** Everything was in one bundle, and our learners are
   explicitly on entry-level Android and metered data.

But a client-side router is the single largest accessibility risk in the redesign, and it is
worth being precise about why.

A tab bar that swaps content in place is *easy* to get right, because there is exactly one
place to do it. `App.tsx` moved focus to `<main>` and announced the change — once, in one
`useEffect`, covering every tab.

A router removes that guarantee. Each route becomes an independent opportunity to forget, and
forgetting is **silent**: nothing errors, nothing looks wrong, and the learner simply finds
that focus is still on the link they pressed, at the top of a document whose entire contents
have changed, with nothing announced.

For a screen-reader user that means re-reading the page to work out what happened. For a
switch-scanning user it means restarting the scan from the top of the document on **every**
navigation — a cost paid repeatedly, by the learners least able to absorb it.

Every published "accessible SPA routing" guide describes the fix. Almost none of them
describe how to stop the fix from being forgotten on route number eleven.

## Decision

**Adopt React Router, and make the safe path the only path.**

Three parts:

1. **Every route renders through a single `<AppRoute>` wrapper** which, on every navigation:
   - moves focus to the new `<main>` (`tabIndex={-1}`, so it is programmatically focusable
     without becoming an obstacle in the tab order),
   - announces the destination through the existing single announcer,
   - sets `document.title`.

2. **The route table is data, not JSX.** `ROUTES` is an array that a test can iterate.

3. **`tests/routes/contract.test.tsx` walks that real table** and asserts all three properties
   for every entry. A route added without the wrapper fails CI at the moment somebody adds it,
   rather than in a learner's session six weeks later.

Point 3 is the actual decision. Points 1 and 2 are how it is made checkable.

### Focus goes to `<main>`, not to the heading

Focusing the `<h1>` reads the heading and then leaves the user *after* it, so Shift+Tab lands
them outside the content they just arrived at. Focusing the container puts them at the start
of the new content with all of it ahead of them, which is what "you have arrived here" should
mean.

### Four surfaces are chromeless

Level, interview, story and onboarding render with no navigation at all. This is the
structural half of "not a dashboard": navigation that stays on screen during a task is
navigation inviting the learner to leave the task. Chromeless does **not** mean no way out —
each carries an explicit way back, because a learner who cannot leave a screen is trapped in
it.

### The navigation is links, not tabs

The old bar announced itself as a `tablist`. That was true when content swapped in place. With
real URLs it would be a lie a screen-reader user has to see through, so the chrome is a real
`<nav>` of `<a>` elements and `aria-current="page"` marks the current one.

## Consequences

**Good.**
- Surfaces are linkable, which is what a trainer assigning work actually needs.
- Route-level code splitting: the entry chunk is **69.8 KB gzipped** against a 120 KB budget,
  with fifteen route chunks loaded on demand. A learner who never opens the trainer dashboard
  never downloads it.
- The back button works, which learners expect and nobody had to be taught.
- Focus, announcement and title behaviour is now *provable* rather than *believed* — which it
  was not before, either, even with one code path.

**Costs.**
- A dependency (`react-router-dom`) on the critical path.
- Boot remains deliberately outside the router. A learner part-way through the four-door
  screen must not reach `/me/settings` with the Back button, because that screen would render
  in a modality they have not chosen yet.
- `BrowserRouter` needs the host to serve `index.html` for unknown paths. Getting this wrong
  produces a 404 on refresh — noted here because it is a deployment step, not a code one.

**Honest deviation from the blueprint.** Phase 1 is described as "nothing user-visible
changes", and this does change one visible thing: the tab bar becomes a navigation bar with
URLs. The blueprint places F2 (the router) in Phase 1 while also calling Phase 1
behaviour-preserving; those cannot both hold, since a router's entire purpose is to change
what the address bar says. The learner-facing *surfaces* are unchanged — same screens, same
content, same tests — and the world map, which is the genuinely new experience, stays behind
the `game_loop` flag where the blueprint puts it.

## Alternatives considered

**Keep the tab bar, add URLs with the History API by hand.** All of the accessibility risk,
none of the code splitting, and a hand-rolled router that would need the same contract test
anyway.

**A route-level `useEffect` in each screen instead of a wrapper.** This is the common
approach and it is exactly the failure mode described above: correct on the day it is written,
missing on the eleventh route. The wrapper exists so the question is never asked again.

**Hash routing.** Avoids the server configuration note, at the cost of URLs a trainer would
have to paste carefully and screen readers announce awkwardly. Not worth it.

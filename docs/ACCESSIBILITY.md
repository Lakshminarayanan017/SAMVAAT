# Accessibility Acceptance Criteria

**Target:** WCAG 2.2 Level AA · IS 17802 (Indian ICT accessibility standard)

This is not a checklist to run before launch. It is the definition of "done" for every screen,
every sprint. Read it before writing any UI.

---

## The rule that does the heavy lifting

> **Feature code may never import a renderer or an input component directly.**
> It renders `<ModalityRouter block={…} />` and `<ModalityInput block={…} onResponse={…} />`.

An ESLint boundary rule (`no-restricted-imports` on `src/modality/**`) enforces this and fails
the build. Everything else in this document is a safety net; this rule is the actual mechanism.

**Why it works:** a developer cannot forget to make a screen accessible, because they never
chose how it renders. The router did, from the learner's Communication Ability Profile.

---

## Automated gates (run in CI, block merge)

| Gate | Tool | Bar |
|---|---|---|
| Accessibility violations | `axe-core` via `@axe-core/playwright` | **Zero** critical or serious, on every route × every modality combination |
| Lighthouse accessibility | `lighthouse-ci` | ≥ 95 |
| Colour contrast | Token-level unit test | ≥ 7:1 body text, ≥ 4.5:1 large text — we exceed AA deliberately |
| Keyboard traps | Playwright tab-sweep | Zero unescapable regions |
| Contract accessibility flags | `packages/contracts` validator | No `ContentBlock` requires a channel without an equivalent representation |
| Timer usage | Static check | No `setTimeout`-driven progression gates in feature code (Ethics E6) |

---

## Manual gates (every sprint, on the top 10 flows)

Automated tooling catches roughly 30% of real accessibility problems. These catch the rest.

| Pass | How |
|---|---|
| **NVDA** (Windows) | Monitor off. Complete the flow. |
| **VoiceOver** (macOS + iOS) | Rotor navigation, heading order sensible. |
| **TalkBack** (Android) | Explore-by-touch, swipe navigation. |
| **Keyboard only** | Unplug the mouse. Visible focus at all times. |
| **Switch access** | Two-switch scanning, real device or key emulation. |
| **400% zoom** | No horizontal scroll, no clipped content, no overlap. |
| **Voice control** | Every interactive element addressable by its visible label. |
| **Cognitive load** | Reviewed by a special educator, not by us. |

---

## Per-screen requirements

### Structure
- One `<h1>` per page; heading levels never skip.
- Landmarks: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>` — one `<main>`.
- Skip link to `<main>` as the first focusable element.
- Page title updates on route change and is announced.

### Focus
- Visible focus indicator on every interactive element, ≥ 3:1 against the adjacent colour, never `outline: none` without a replacement.
- Focus moves into a dialog on open and **returns to the trigger** on close.
- Focus never moves without user action, except into a newly opened dialog.
- Logical tab order matching visual order.

### Announcements
- Use the single global `<Announcer />`. Do not scatter `aria-live` regions.
- `polite` for status; `assertive` only for errors that block progress.
- Every async action announces its start and its result. Silence is a bug.

### Targets and motion
- Minimum 44×44 CSS px, configurable to 88px via the Communication Ability Profile.
- ≥ 8px spacing between adjacent targets.
- No drag-only interaction — always a tap/click/keyboard alternative.
- `prefers-reduced-motion` respected globally. **No animation ever carries information.**

### Forms
- Every input has a visible, programmatically associated `<label>`. Placeholders are not labels.
- Errors are announced, described in text, and identify the field by name.
- Errors state how to fix, not just what is wrong.
- No input is invalidated on blur while the user is still typing.

### Content
- Nothing conveyed by colour alone.
- Nothing conveyed by position alone.
- All images have `alt`; decorative images have `alt=""`.
- All media has captions, and a transcript.
- Link text makes sense out of context — never "click here", never "read more".

### Data visualisation
Every chart ships with **all three**:
1. The visual chart
2. An equivalent `<table>` (may be visually hidden, must be reachable)
3. A one-sentence text summary of the trend

---

## Easy-Read requirements

For profiles with `text_complexity: easy_read`, enforced by the `EasyReadText` component and a
lint rule on content source:

- ≤ 15 words per sentence
- One clause per line, one idea per screen
- Common words only — no jargon, no idiom, no metaphor
- Sans-serif, ≥ 18px, line height ≥ 1.5
- Left-aligned, never justified
- A supporting image beside each idea
- Active voice, present tense, second person

---

## What we do *not* do

| Anti-pattern | Why |
|---|---|
| An "accessibility mode" toggle | Accessibility is the architecture, not a mode. See the Modality Router. |
| An overlay/widget (accessiBe-style) | They do not work, and disabled users overwhelmingly report they make things worse. |
| `aria-label` to patch a bad structure | Fix the structure. ARIA is a last resort, not a first tool. |
| Hand-rolled dialogs, menus, tabs | Use Radix primitives. Focus management is harder than it looks. |
| Testing only with automated tools | They catch ~30%. Run the manual passes. |
| Shipping "we'll make it accessible later" | There is no later. It becomes a rewrite. |

---

## Reporting

Every PR description includes:

```
Personas tested: P1, P4
axe: 0 critical, 0 serious
Manual: keyboard ✓  NVDA ✓  switch-scan n/a
```

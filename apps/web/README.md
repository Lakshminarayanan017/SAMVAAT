# apps/web — learner app & dashboards

**Module M2** · React 18 · TypeScript · Vite

The client. Contains the **Modality Router** — the piece that makes this product
architecturally accessible rather than accessible by discipline.

---

## Run it

```bash
npm install                    # from the repository root
npm run contracts:build        # generates the types this app imports
npm run dev:web                # http://localhost:5173
```

```bash
npm run typecheck -w @samvaad/web
npm run lint      -w @samvaad/web
npm run test      -w @samvaad/web
```

The dev server opens the **channel comparison view** — one authored ContentBlock rendered
through all five output channels, with a switcher for the five personas. That screen is
milestone MS2's proof, and the most persuasive thing to show anyone evaluating this project.

---

## Layout

```
src/
├── modality/          ★ THE MODALITY ROUTER — read this first
│   ├── ModalityRouter.tsx   profile in, rendered experience out
│   ├── registry.ts          channel → renderer map (internal)
│   ├── register.ts          registers every renderer, once, at import
│   └── renderers/           one renderer per output channel
├── a11y/
│   ├── ProfileProvider.tsx  the Communication Ability Profile, in context
│   └── Announcer.tsx        the single aria-live region for the whole app
├── design-system/
│   ├── tokens.ts            colour/type/spacing + runtime theme applier
│   └── contrast.ts          WCAG luminance and contrast maths
├── features/                feature code. May ONLY use <ModalityRouter/>
└── styles/global.css
tests/
```

---

## The one rule

> **Feature code may never import a renderer or the registry.**
> It renders `<ModalityRouter block={…} />` and lets the profile decide.

This is enforced by `no-restricted-imports` in [eslint.config.js](eslint.config.js), and
[tests/modality/boundary.test.ts](tests/modality/boundary.test.ts) runs ESLint over
deliberately non-compliant code to prove the rule still fires. A rule nobody tests is a rule
that has silently stopped working.

**Why it works:** a developer cannot forget to make a screen accessible, because they never
chose how it renders. See [ADR-0001](../../docs/ADR/0001-modality-neutral-content.md).

---

## How the router decides

```
CommunicationAbilityProfile.output_channels = ['easy_read', 'pictograph', 'audio']
                                                    │           │          │
                                                 PRIMARY      support    support
                                                    ▼           ▼          ▼
                          ┌──────────────────────────────────────────────────┐
                          │  all three render SIMULTANEOUSLY, from one block │
                          └──────────────────────────────────────────────────┘
```

If a representation is missing, it degrades along a documented chain
(`isl → captioned_text → easy_read`, and so on) rather than showing an empty screen. Missing
representations are also a build-time warning from the content validator, so they surface to
the team before they surface to a learner.

---

## Design tokens

Defined in TypeScript, not CSS, for two reasons:

1. A unit test proves **every** foreground/background pair in **all four themes** clears its
   contrast bar — body text at 7:1 (WCAG AAA, because low vision is persona P1, not an edge
   case) and non-text UI at 3:1. This caught a border colour at 2.56:1 on the first run.
2. `applyTheme` writes CSS custom properties at runtime, so a learner switching to high
   contrast mid-session sees it immediately.

There are four themes because contrast preference and colour scheme are **independent axes**.
Someone may want dark mode without high contrast. Collapsing them forces a choice nobody
should have to make.

---

## Accessibility expectations

Every PR: see [docs/ACCESSIBILITY.md](../../docs/ACCESSIBILITY.md). In short —

- Use the single `<Announcer />`; do not scatter `aria-live` regions.
- Use real form controls. A styled `<div>` costs you keyboard, screen reader and voice control.
- Minimum 44×44px targets, raised to 88px by the profile for motor impairment.
- No animation carries information; `prefers-reduced-motion` is respected globally.
- **No time-pressure mechanics, ever** (Ethics E6).

---

## Not yet built

`[M2]` Input adapters (`ModalityInput`) — speech, text, AAC board, sign, switch-scan.
`[M15]` Service worker, IndexedDB cache, on-device ASR.
`[M14]` Dashboards. `[M1]` Onboarding and the four-door screen.

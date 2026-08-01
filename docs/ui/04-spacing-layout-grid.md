# 04 · Spacing, layout and grid

---

## 1. What Duolingo does

### A 4px base, used at 8/12/16/24 in practice

Almost every gap in the interface is one of four values. Screen gutters are 16px on phone.
Cards use 16px internal padding. Stacked items sit 12px apart. Sections are separated by 24px.

### Content is column-capped and centred

On tablet and desktop the content column stops at roughly 600px and centres. The app never
becomes a wide two-column layout — the phone layout simply floats in the middle of a larger
screen.

### The primary action is bottom-anchored

Inside a lesson, the CTA is fixed to the bottom edge with the safe-area inset respected. It does
not scroll with the content. The learner's thumb finds it without looking.

### Vertical rhythm is generous

Nothing is cramped. There is more whitespace than a productivity app would use, and the effect
is that each screen reads as having one job.

### Observed structure of a lesson screen

```
┌─────────────────────────────┐
│ [×]  ▓▓▓▓▓▓░░░░░░  [♥ 5]    │  56px  chrome
├─────────────────────────────┤
│                             │  24px
│  Question prompt            │
│                             │  24px
│  ┌───────────────────────┐  │
│  │ option                │  │  ~64px each
│  └───────────────────────┘  │  12px gap
│  ┌───────────────────────┐  │
│  │ option                │  │
│  └───────────────────────┘  │
│                             │
│         (flex spacer)       │
├─────────────────────────────┤
│  [   CHECK   ]              │  ~88px  bottom-anchored
└─────────────────────────────┘
```

---

## 2. Why it works

- **Four spacing values** means two screens built by two people look the same. A freeform
  spacing system guarantees drift.
- **The column cap** means one layout is designed, tested and maintained — not three.
- **Bottom-anchored CTA** puts the most-used control in the easiest place to reach one-handed,
  and in the same place on every screen, so it becomes muscle memory.
- **Generous rhythm** reduces the working-memory cost of parsing the screen, which matters more
  in a learning context than information density does.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| 16px gutters at 400% zoom | Content is 320px wide at that zoom; 16px gutters plus a full-width card leaves almost nothing. Layout must reflow, not just shrink |
| Fixed bottom CTA overlapping content | At large text sizes the CTA can cover the last option. WCAG 2.2 SC 2.4.11 (Focus Not Obscured) is exactly this failure |
| Options at ~64px | Fine at the 44px floor, insufficient once a learner sets 88px targets — the layout has no room reserved for it |
| Horizontal rows of counters in the header | The first thing to break at 400% zoom |
| No landmark structure | The header/main/nav regions are visual only, so a screen-reader user cannot jump between them |

---

## 4. SAMVAAD specification

### Scale

| Token | Value | Typical use |
|---|---|---|
| `--s-1` | 4px | Icon-to-label |
| `--s-2` | 8px | Inside a chip |
| `--s-3` | 12px | Between stacked list items |
| `--s-4` | 16px | Card padding, screen gutter (phone) |
| `--s-5` | 24px | Between blocks |
| `--s-6` | 32px | Between sections |
| `--s-7` | 48px | Above a screen's primary action |
| `--s-8` | 64px | Screen top/bottom breathing |

Nothing outside this scale. There is no `<Spacer>` component, because a spacer is the documented
way to bypass the scale.

### Layout

| Breakpoint | Behaviour |
|---|---|
| ≤ 599px | Single column, 16px gutters, bottom nav |
| 600–899px | Single column, 24px gutters, bottom nav |
| 900–1199px | Content 44rem centred, **side** nav |
| ≥ 1200px | Content 48rem centred, side nav, wider gutters |

**Missions are always single column**, at every width. A mission is one thing.

### Zoom is a first-class breakpoint

At 400%, a 1280px viewport behaves as 320px. Every layout is verified there, and horizontal
scroll is a build failure, not a visual nit.

Consequences that follow:
- All horizontal groups wrap by default
- Grids use `repeat(auto-fit, minmax(min(16rem, 100%), 1fr))` — the `min()` is what stops
  overflow below the track size
- Any genuinely un-wrappable element (a wide table) scrolls **inside its own container**, never
  the page

### The bottom action bar

Bottom-anchored, but **not** `position: fixed` over content. It is a flex sibling of a scrolling
content region, so it can never obscure the last item. The container reserves its height.

```
[ scrolling content region ]  flex: 1, overflow-y: auto
[ action bar              ]  flex: 0 0 auto, safe-area padding
```

This costs nothing and removes an entire class of WCAG 2.4.11 failure.

### Target sizes

Floor is `--target-min`, which the learner's profile sets between **44px and 88px**. No component
hard-codes 44. Layouts are built so that raising the target to 88px reflows rather than overlaps —
verified by rendering the mission screen at 88px in the test suite.

### Landmarks

Every screen has real regions: `<header>`, `<nav aria-label="Main">`, `<main>`. A screen-reader
user jumps between them; a sighted user never notices they exist. This is free and is skipped
approximately always.

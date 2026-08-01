# 09 · Navigation and information architecture

---

## 1. What Duolingo does

### Five bottom-bar destinations, never more

```
Learn  ·  Practice  ·  Leagues  ·  Quests  ·  Profile
```

Icon plus label, always both. The active one is filled and coloured; the rest are outlined grey.
The bar is fixed to the bottom edge, thumb-reachable, and present on every screen **except**
inside a lesson.

### A lesson removes all navigation

Entering a lesson replaces the whole screen. No bottom bar, no header — only a close button, a
progress bar and hearts. There is no way to wander off mid-lesson by accident.

### The header is four glanceable counters

Language flag · streak · gems · hearts. Tapping any opens its own detail sheet. No labels — icons
and numbers only.

### Depth is shallow: two levels, mostly

Almost everything is *tab → detail sheet*. Very little is three levels deep. Back is nearly always
"close this sheet" rather than "return through a stack".

---

## 2. Why it works

- **Five destinations** is at the limit of what can be scanned without reading. Six starts
  requiring thought.
- **Bottom placement** is the reachable zone one-handed, which is how the product is actually used.
- **Removing navigation inside a lesson** is the structural expression of "this is a task, not a
  page". It is the single biggest reason the lesson feels like a game rather than a form.
- **Shallow depth** means a learner never gets lost, and never needs to understand a hierarchy.
- **Sheets over pushes** keeps context visible behind the sheet, so dismissing feels like
  returning rather than navigating.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| No URLs at all | A trainer cannot send a learner to a specific level. "Open the app, press Learn, scroll to unit 5" is not a link |
| Header counters unlabelled | A screen reader reads four bare numbers |
| Icon-only distinctions in the tab bar rely partly on colour | Active/inactive must not be colour-only |
| A fixed bottom bar overlapping content at large text | WCAG 2.4.11 failure |
| Sheets that trap focus badly | Common failure; focus must move in *and* be restored on close |

---

## 4. SAMVAAD specification

### Destinations — five, role-dependent

| Destination | Route | Icon | Shown to |
|---|---|---|---|
| Home | `/` | map | everyone |
| Practice | `/practice` | repeat | everyone |
| Stories | `/stories` | speech-bubbles | everyone |
| Me | `/me` | person | everyone |
| My learners | `/trainer` | people | trainers |
| Cohort | `/institution` | chart | institutions |

A learner sees four. A trainer sees five. Never more than five at once.

**Icon *and* label, always.** Icon-only navigation is unusable for a learner with an intellectual
disability and ambiguous for everybody else. The label is not a tooltip; it is on screen.

### Full route map

```
/                       Home — the path
/world/:id              One world, linkable
/level/:id              Level runner            ┐
/practice               Daily review            │ full-screen,
/story/:id              Story runner            │ no chrome
/interview              Mock interview          ┘
/stories                Story chooser
/me                     Progress, achievements
/me/data                Export and erasure
/me/settings            How this app talks to me
/trainer                Trainer dashboard        (role)
/institution            Cohort report            (role)
/demo                   Channel comparison       (hidden from nav)
```

### Four surfaces are chrome-free

`/level/:id` · `/practice` · `/story/:id` · `/interview`

A learner mid-mission sees the mission and nothing else. This is the structural half of "not a
dashboard".

**Chrome-free does not mean trapped.** Every one carries an explicit, always-visible way out
(`Back to my map` / `Stop for now`), and leaving never warns about losing progress.

### The header

Deliberately not four counters. On the home screen only:

```
[ Mitra ]  SAMVAAD              [ streak ] [ XP ]
```

Both counters are **icon + number + accessible label** —
`aria-label="5 day streak"`, `aria-label="340 XP"` — never a bare number. There is no gem counter
and no heart counter, because neither exists.

### Navigation is links, not tabs

Real `<a>` elements inside `<nav aria-label="Main">`, with `aria-current="page"` on the active
one. The previous build announced itself as a `tablist`, which was true when content swapped in
place and is a lie once these are URLs.

Active state carries **three** signals: fill, weight, and `aria-current`.

### The bottom bar does not overlap

It is a flex sibling of the scrolling region, not `position: fixed` over it. The container
reserves its height, so it can never obscure the last item at any text size.

At ≥900px it becomes a **side** navigation and the content column centres beside it.

### The accessible route contract

Every route renders through one wrapper which, on every navigation:

1. moves focus to the new `<main>` (`tabIndex={-1}`)
2. announces the destination once
3. sets `document.title`

A test walks the real route table and fails any route that does not. This is the single largest
accessibility risk in a client-routed app: forgetting is silent, and the learner simply finds
focus still on the link they pressed with nothing announced.

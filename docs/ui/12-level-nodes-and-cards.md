# 12 · Level nodes and cards — every state

---

## 1. What Duolingo does

### The node is a circle, and its state is its appearance

| State | Appearance |
|---|---|
| Locked | Flat grey circle, padlock glyph |
| Available | Coloured circle, unit hue, star glyph |
| Active | Larger, brighter, bouncing, START pill above |
| Complete | Solid gold/coloured, check glyph |
| Legendary | Purple/gold, crown glyph |

Diameter roughly 72–80px; the active one grows to ~90px.

### Tapping opens a popover, not the lesson

```
┌─────────────────────────┐
│  Order food             │
│  Lesson 3 of 6          │
│  ┌───────────────────┐  │
│  │      START        │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

A confirmation step that also carries information the circle could not.

### Crown levels

A completed lesson can be repeated to raise its crown level, shown as small pips. This is what
turns a finite course into an indefinite one.

---

## 2. Why it works

- **A circle is a strong, scannable shape** and reads as a "step" more naturally than a rectangle.
- **The popover carries the name and position** the circle cannot, and confirms an accidental tap.
- **Crowns give completed content a reason to exist.** Without them a finished course is dead
  weight.
- **Size difference for the active node** does more work than colour — it survives greyscale.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| A circle with a glyph and no text | "Button" is all a screen reader gets |
| Padlock | Reads as "not for you" |
| State by fill colour | Colour-only |
| Circles are hard to hit precisely | ~76px circle has less effective target area than a 76px rectangle, and the corners are dead. Costly for a motor impairment |
| Popover as an extra step | Two taps for every lesson; for a switch user, two full scan cycles |
| Bouncing active node | Permanent motion |

---

## 4. SAMVAAD specification

### Rows, not circles

A level is a **full-width row**, not a circle. Reasons:

- The whole row is the target, so effective hit area is far larger than a circle of the same
  nominal size — this matters most for the learners who need it most
- It reflows at 400% zoom; a circle grid does not
- It has room for the level name, the star count and the state, **as text**
- It reads correctly in a list to a screen reader

### The row

```
┌──────────────────────────────────────────────────┐
│  ✓   Asking someone to repeat          ★ ★ ☆     │
│      Done · 2 of 3 stars                          │
└──────────────────────────────────────────────────┘
```

Minimum height `--target-min` (44–88px per profile). Full-width. Real `<button>`.

### Every state, fully specified

| State | Glyph | Border | Fill | Accessible name |
|---|---|---|---|---|
| **Not started** | ○ | 1px `--line` | `--surface` | `"Asking someone to repeat. Not started."` |
| **Next** | ▶ | 2px `--brand` | `--surface` | `"Asking someone to repeat. Next. 4 things to try."` |
| **In progress** | ◐ | 2px `--brand` | `--surface` | `"Asking someone to repeat. 2 of 4 done."` |
| **Done** | ✓ | 1px `--line` | `--sunken` | `"Asking someone to repeat. Done. 2 of 3 stars."` |
| **Mastered** | ✓ | 2px `--good-ink` | `--good-wash` | `"Asking someone to repeat. Done. 3 of 3 stars."` |
| **Ahead** | — | 1px dashed `--line` | `--surface` | `"Asking someone to repeat. Further on — you can still try it."` |

Every state has **glyph + border + fill + text**. Remove colour entirely and all six remain
distinguishable.

**There is no locked state.** `Ahead` is the closest thing and it is fully pressable.

### No popover

Pressing a level opens the level. The name, position and mission count are already **on the row**,
so the popover carried nothing the row does not.

Removing it saves every learner one tap per session, and saves a switch user an entire scan cycle
per session — which over a year is a large amount of somebody's life.

### Stars

Three per level:

| Star | Earned by |
|---|---|
| 1 | Finishing. Always earned, regardless of accuracy |
| 2 | Most missions right |
| 3 | **Coming back** and still holding it — FSRS stability past the reliability threshold |

The third star cannot be earned in one sitting, by design. It is the mechanic that makes
returning meaningful without any loss-aversion, and it is honest: the product's central claim is
retention, so the top reward is retention.

Rendered as filled/empty glyphs with `aria-label="2 of 3 stars"` on the group. Individual stars
are `aria-hidden` — five separate announcements bury the fact in noise.

### No crown levels

Replaced by the third star plus ordinary FSRS review. Crowns exist to make a finished course
indefinitely repeatable, which is a retention mechanic for a consumer app. Our retention mechanic
is spaced repetition, which is the real version of the same idea.

### Motion

A row that changes state (a star landing) uses a single **420ms** transition, once, and never
loops. The `Next` row is identified by border weight, glyph and text — not by movement.

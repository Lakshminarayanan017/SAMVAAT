# 10 · Home and the path

**The most important screen in the product.** Everything else is reached from here, and the
decision made in the first two seconds on this screen determines whether a session happens.

---

## 1. What Duolingo does

### The screen is the path and nothing else

No dashboard, no stats summary, no "welcome back", no recommendations list. A vertical winding
trail of circular nodes, one section at a time, scrolled vertically.

### One node is obviously next

The active node sits under a bouncing **START** pill. It is larger, filled, and animated. Every
other node is either completed (solid, with a check or crown) or upcoming (flat grey).

### A sticky section header

As you scroll, a coloured band stays pinned at the top:

```
┌──────────────────────────────────────┐
│  SECTION 2, UNIT 5                   │
│  Order food                     [📖] │
└──────────────────────────────────────┘
```

Unit name, position, and a guidebook button. The band takes the unit's colour, so scrolling
through the course is visibly moving through coloured regions.

### Characters flank the path

Illustrations sit beside the trail at intervals. They mark places and break up a long scroll.

### The path curves

Nodes alternate left-of-centre and right-of-centre in a gentle S. Purely aesthetic.

### Layout

```
       ●  done
    ●     done
       ●  done
          ┌─────────┐
          │  START  │   ← bouncing
          └─────────┘
       ◉  ACTIVE (larger, filled)
    ○     upcoming
       ○  upcoming        🐦  character
    ○     upcoming
```

---

## 2. Why it works

- **The path is the progress bar for the whole course.** You see where you have been and where
  you are going in one view, with no chart and no numbers.
- **One obvious next node removes the opening decision.** The most fragile moment in any session
  is the two seconds after opening; this screen has exactly one answer to "what now".
- **Completed nodes accumulate visibly.** Scrolling up is a record of work done — the cheapest and
  most effective motivator in the product.
- **Sections give a long course spatial memory.** "The blue unit" is a real place a learner
  recalls.
- **Upcoming nodes are visible, not hidden.** You can see what is coming, which frames the course
  as finite and achievable.

---

## 3. Where it fails our learners

This screen is where Duolingo's design is *least* transferable. Nearly every element that makes
it delightful for a general user fails one of our personas.

| Problem | Who it fails |
|---|---|
| **The curve encodes order in 2D position** | A screen reader receives a flat sequence of buttons; the curve conveys nothing. Switch scanning must traverse a zig-zag, which row-column scanning handles badly. At 400% zoom the path either breaks or forces scrolling in two directions — a 1.4.10 reflow failure. On a narrow phone it compresses to near-vertical anyway, so the aesthetic is lost exactly where most learners are |
| **Padlocks on upcoming nodes** | A padlock on a product built for disabled people reads as "not for you". These learners have met enough locked doors |
| **State is a coloured circle** | Done/active/upcoming distinguished by fill and colour, with no text |
| **Bouncing START loops forever** | Permanent motion for someone trying to read the screen |
| **Nodes are unlabelled circles** | "Button, button, button, button" |
| **No indication of what a node contains** | You press it to find out |

---

## 4. SAMVAAD specification

### It is a vertical list, not a winding path

This is a deliberate, recorded decision and it will be proposed again, so the reasoning is here:

A vertical list of worlds — each expanding into chapters and levels — carries **identical
information** to the curve, and reflows, scans and reads correctly with no special handling. The
delight comes from world identity, stars, motion and Mitra. **None of that needs a curve.**

A decorative path drawn *behind* an already-correct list is a fine V2 idea. Building the path
first and retrofitting accessibility is not.

### Structure

```
┌─────────────────────────────────────────┐
│ [Mitra]  SAMVAAD      🔥 5 day   ⭐ 340 │   header
├─────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐ │
│ │  Next up                            │ │   ← the one primary action
│ │  Asking someone to repeat            │ │
│ │  World 2 · 4 things to try           │ │
│ │  ┌───────────────────────────────┐  │ │
│ │  │          Continue             │  │ │
│ │  └───────────────────────────────┘  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│  Your worlds                            │
│ ┌─────────────────────────────────────┐ │
│ │ ◆ 1  Finding Your Voice             │ │   ← expanded (current)
│ │      ●●●○○   3 of 5 levels          │ │
│ │      ┌─────────────────────────┐    │ │
│ │      │ ✓ First words    ★★★    │    │ │
│ │      │ ✓ Saying hello   ★★☆    │    │ │
│ │      │ ▶ Introducing…   ☆☆☆    │    │ │
│ │      └─────────────────────────┘    │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ ◆ 2  Making Sure You Understand  ▾  │ │   ← collapsed
│ │      2 of 5 levels                  │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### The "Next up" card

The single most important element on the screen.

- **Largest thing on the page**, `lifted` elevation, brand-filled primary button
- **Resolves to a specific level** — no decision required
- Names the level and its world, so pressing is informed rather than blind
- States how many missions, so **the end is visible before the beginning**
- Never says "resume" or "you left off" — that frames the last session as unfinished

### World rows

Each world is a **collapsible section**, current world open, everything else closed. A
screen-reader user is never made to walk past fifty levels to reach the end of the list.

Every world carries **three independent identity signals**:
1. Colour (verified 7:1, and distinguishable in greyscale by lightness)
2. Icon silhouette, chosen to differ in *outline* at 32px monochrome
3. Number and name, always as text

### Level rows

| State | Visual | Text | Never |
|---|---|---|---|
| Done | check glyph + filled stars | `"Done. 3 of 3 stars."` | — |
| Next | arrow glyph + brand outline | `"Next. Not started."` | — |
| Ahead | plain, normal weight | `"Further on — you can still try it"` | **no padlock** |

**Nothing is locked.** A level further along is `AVAILABLE_EARLY`, not `LOCKED`. Mastery gates
**stars**, which are optional. It never gates **access**, which is not. The learner most likely
to need interview practice tomorrow is the least likely to have time for fifty levels first.

### Progress is text first

`"3 of 5 levels"` is the accessible name. The dot row is `aria-hidden` decoration over it.

### No looping animation

The "press here" job is done by size, position, fill and the word `Continue`. Worlds stagger in
once on first paint at 40ms intervals, capped at 8 — and not at all under reduced motion.

### Empty state — a brand-new learner

No "0 of 50" and no empty progress bars. A first-time learner sees the Next-up card with
`"Start here"` and a single world open. Zeroes everywhere is a screen that says *you have done
nothing*, which is a poor first impression of a product about capability.

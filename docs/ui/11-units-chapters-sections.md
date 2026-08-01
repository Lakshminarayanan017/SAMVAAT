# 11 · Units, chapters and sections

---

## 1. What Duolingo does

### Three levels of grouping

```
Section  →  Unit  →  Lesson
```

A **section** is a large band of the course (roughly a CEFR level) with its own colour and a
full-width introduction card. A **unit** is ~5–8 lessons around one topic, with a sticky header.
A **lesson** is one node on the path.

### The unit header is a persistent contract

Pinned while you scroll through that unit:

```
┌────────────────────────────────────┐
│ UNIT 5                             │
│ Order food                    [📖] │
└────────────────────────────────────┘
```

It answers "where am I and what am I learning" without the learner asking.

### The guidebook

A per-unit reference: the key phrases, grammar notes, examples. Available before, during and
after. It is explicitly *not* a lesson — it is the thing you consult.

### Sections gate access

A section unlocks when the previous one is finished, or via a jump test.

### Colour banding

Each section owns a hue that appears on the header, the nodes and the lesson chrome.

---

## 2. Why it works

- **Three levels is the maximum a learner will hold.** Two is too flat for a 200-lesson course;
  four is a filing system.
- **The sticky header removes "what am I doing"** from working memory during the scroll.
- **The guidebook separates reference from practice.** Trying to teach and test in the same
  surface makes both worse.
- **Colour banding gives spatial memory** to a long course.
- **A unit is a *completable* chunk.** Finishing a unit is a real event at a satisfying interval —
  more often than a section, less often than a lesson.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Section gating | A hard wall. Our learner may need World 10 (interviews) *this week* |
| The guidebook is text-only | Not available in symbols, Easy-Read or ISL — so the reference material is less accessible than the lessons |
| Sticky header eats vertical space at 400% zoom | At that zoom the header can occupy a third of the viewport |
| Unit identity is largely colour | Colour-only grouping |
| No indication of length before entering | A learner budgeting energy cannot |

---

## 4. SAMVAAD specification

### Our three levels

```
World  →  Chapter  →  Level
```

10 worlds · 15 chapters · 50 levels, already authored and resolved against the phrase bank at
build time so the journey cannot drift from the corpus.

| Level | Size | Represents |
|---|---|---|
| **World** | 3–6 chapters | A communication domain — *Speaking Up For Yourself* |
| **Chapter** | 2–5 levels | A situation — *Asking for an adjustment* |
| **Level** | 3–6 missions | One sitting, 3–7 minutes |

### Nothing gates access

A world further along is **available early**, captioned *"Further on — you can still try it"*.

Mastery gates **stars**. It never gates **access**. Two reasons, and both matter:

1. Ethics E7 — a feature that fails a persona is not shippable, and a gate a learner cannot pass
   fails them permanently.
2. The learner most likely to need interview practice *tomorrow* is the one least likely to have
   time for fifty levels first.

### The world header is not sticky

It scrolls away. At 400% zoom a sticky header consumes a third of the viewport, and the
information it carries — which world, which chapter — is already in the route title, which is
announced on arrival and shown in the browser tab.

### Chapters expand in place

```
◆ 5   Speaking Up For Yourself                      ▾
      ●●●○○  3 of 5 levels · 8 of 15 stars

      ── Asking for what helps ──────────────────
      ✓  What I need to do my job     ★★★
      ✓  Asking early                 ★★☆
      ▶  When the answer is no        ☆☆☆   Next

      ── Telling someone ⚑ ──────────────────────
         Saying it in my own words    ☆☆☆
         Further on — you can still try it
```

One world open at a time. A screen-reader user is not walked past fifty levels.

### Sensitive chapters are flagged before entry

Chapters covering disclosure and adjustments carry `sensitive: true`. Before the learner enters,
the chapter states plainly that they can stop at any time, that nothing is recorded as a failure,
and that nobody is told they left.

Shown **before** starting, not after. A learner about to rehearse telling an employer they are
disabled is rehearsing something with real consequences, and being shown the exit once they are
already upset is being shown it too late.

### Length is stated before entry

Every level row states its mission count. A learner budgeting limited energy — which describes
several of our personas on most days — can choose a level that fits what they have.

### The guidebook becomes "What this is for"

Per chapter, and it goes through the **modality router** like everything else, so it arrives as
Easy-Read, symbols, audio or ISL according to the profile.

Reference material that is less accessible than the lessons is a real and common failure. Ours
uses the same rendering path, so it cannot happen.

### World identity

Three signals, always: **colour** (7:1, lightness-distinct so greyscale still separates them),
**icon silhouette** (differing in outline at 32px monochrome), and **number + name as text**.

Roughly one man in twelve has a colour vision deficiency. A map encoding identity only in hue
tells him nothing.

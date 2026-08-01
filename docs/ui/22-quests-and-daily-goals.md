# 22 · Quests and daily goals

---

## 1. What Duolingo does

### The daily goal

Chosen at onboarding — Casual 5 / Regular 10 / Serious 15 / Intense 20 XP per day. Shown as a ring
that fills. Hitting it triggers a small celebration and feeds the streak.

### Daily quests

Three per day, refreshing at midnight:

> Earn 20 XP · Get 5 in a row correct · Complete 2 lessons

Completing all three fills a chest.

### Monthly challenge

A calendar; complete a quest each day to fill a badge. Missing a day leaves a visible gap in the
grid.

### Friend quests

Paired with another learner; you both contribute to a shared target.

---

## 2. Why it works

- **A goal converts an open-ended activity into a completable one.** "Practise Spanish" has no
  end; "20 XP" does.
- **Three quests give variety** without requiring the learner to invent their own objective.
- **The ring is glanceable** — progress without reading.
- **A monthly grid makes consistency visible** over a longer horizon than a streak number.
- **Friend quests add social obligation**, which is the strongest retention force available.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Goal in XP** | XP varies by activity, so an XP goal is really "do more of whatever pays fastest" |
| **"Get 5 in a row correct"** | A quest that requires accuracy. A learner having a bad day cannot complete it, and it now reads as a task they failed |
| **The monthly grid shows gaps** | A visual record of every day the learner was too unwell to practise, kept for a month |
| **Friend quests create obligation** | Letting someone else down is a heavy mechanic to point at a population with elevated anxiety, and it is not opt-out in practice |
| Midnight reset | Punishes a learner in a different timezone from their account, or one whose day genuinely runs late |

---

## 4. SAMVAAD specification

### The daily goal is the learner's own session length

Not a menu of four XP targets. Derived from `session_length_target_min`, which the profile sets
between **4 and 8 minutes** — AAC composition is genuinely slower, ADHD profiles want shorter,
and neither is a preference the learner should have to translate into an XP number.

Displayed as *time practised toward their own target*, and the target is changeable at any time
from settings.

### Missing the goal produces nothing

- No red
- No zero
- No "you missed it"
- No notification
- No mark in any grid or calendar

The ring simply is not full, and tomorrow it starts again. There is **no record kept of days
missed**, anywhere in the product, because such a record has no use except to be shown to
somebody.

### Quests are additive only, and never require accuracy

**Daily — one, not three.** Three is a checklist; one is an invitation.

Examples of valid daily quests:

> Finish a level in any world
> Try a phrase you found hard last week
> Read a story

Examples that are **not permitted**, and the rule they break:

| Invalid quest | Rule broken |
|---|---|
| "Get 5 in a row correct" | Requires accuracy |
| "Finish a level in under 4 minutes" | Requires speed |
| "Practise 3 days running" | Punishes an absence retroactively |
| "Beat your score from Tuesday" | Competes the learner against themselves as a target |

### Weekly — three, one of which is always a *courage* quest

> Try a level further on than the one you are up to
> Read a story again and pick a different answer
> Practise saying what helps you at work

**Courage quests reward the attempt, never the outcome.** Attempting is the entire completion
condition. This is the mechanic most worth having, because attempting something above your level
is the behaviour hardest to sustain and the one that most changes what a learner believes they
can do.

### No monthly grid

Replaced by *days practised* — a number that only rises. A grid's whole function is to make gaps
visible, and there is no version of that which is kind here.

### No friend quests, no shared targets, no social obligation

Nothing in this product makes one learner's progress visible to another, or makes one learner's
inactivity into another's problem. See file 23.

### The day boundary is the learner's local midnight

With a **4-hour grace window**, so somebody practising at 1am is credited to the day that just
ended rather than losing it to a clock.

### Presentation

```
┌────────────────────────────────┐
│  Today                          │
│  ◔  4 of 6 minutes              │
│                                 │
│  Today's quest                  │
│  ○ Finish a level in any world  │
└────────────────────────────────┘
```

Ring is `aria-hidden`; the accessible name is `"4 of 6 minutes practised today"`. A quest states
its completion condition in full — no hidden goals, because a hidden goal is a dark pattern and a
visible one is a map.

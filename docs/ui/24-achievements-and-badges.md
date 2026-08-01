# 24 · Achievements and badges

---

## 1. What Duolingo does

### ~15 achievement families, each with 10 tiers

Wildfire (streak) · Sage (XP) · Scholar (words) · Regal (league) · Champion (courses) ·
Sharpshooter (accuracy) · Legendary · Weekend Warrior · Photogenic · Friendly · and others.

### Tiers escalate steeply

Wildfire: 3 → 7 → 14 → 30 → 50 → 100 → 180 → 365 → 500 → 1000 days.

### The grid

A page of badge tiles, each with its art, current tier, and a progress bar to the next.

### Locked achievements are visible but greyed

You can see what exists and how far off you are.

---

## 2. Why it works

- **Ten tiers per family** means there is always a next one close enough to matter.
- **Visible progress bars** convert a distant goal into an incremental one.
- **Showing the full catalogue** gives the product a visible horizon — a map of what is possible.
- **Variety of families** means different play styles all have something progressing.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Sharpshooter** (accuracy-based) | Rewards being right. A learner with aphasia or an intellectual disability can never reach the higher tiers — a permanently visible ceiling with their name on it |
| **Regal** (league-based) | Rewards competitive ranking |
| **Weekend Warrior / streak families** | Rewards uninterrupted availability, which is exactly what a chronic condition removes |
| Steep late tiers (500, 1000 days) | Effectively unreachable, so the grid's later half is permanently grey |
| Badge art with no text | Unusable for P1 |
| A grid of mostly-grey tiles | Reads as a list of things you have not done |

The pattern: most families reward **capacity** — accuracy, speed, uninterrupted time — rather than
**behaviour**. Capacity is what disability affects.

---

## 4. SAMVAAD specification

### Four families, and every one rewards behaviour rather than capacity

| Family | Rewards | Example |
|---|---|---|
| **Consistency** | Coming back | *Practised on 30 days* |
| **Mastery** | Phrases held over time | *50 phrases you still know a month later* |
| **Courage** | Attempting hard things | *Tried a level above where you were* · *Practised telling someone what helps you* |
| **Growth** | Beating your own baseline | *Above where you started, four weeks running* |

**Courage is the one that matters most.** It rewards the attempt, never the outcome — which is
the behaviour hardest to sustain, most affected by anxiety, and most directly connected to what
this product exists to change.

### What is never a badge

- Accuracy or a percentage correct
- Speed or completion time
- Streak *length* as an unbroken run (consistency counts **days practised**, which never falls)
- Rank, league, or anything comparative
- Anything a learner's disability makes unreachable

That last one is the acceptance test for a new badge: **could a learner using any of our sixteen
profiles reach this?** If the answer is no for any of them, it is not a badge.

### Tiers are shallow

Three per family, not ten: **Started · Going · Held**.

Ten tiers with a 1000-day top exists to keep a consumer app alive for three years. Ours does not
need that, and a permanently-unreachable top tier is a ceiling drawn on the learner's own profile
page.

### The catalogue is fully visible from day one

Hidden goals are a dark pattern; visible ones are a map. Every badge shows:

- its **name and its condition, in words** — always
- whether it is earned
- progress toward it, as text and a bar

### Presentation

```
┌─────────────────────────────────────────────┐
│  Courage                                    │
│                                             │
│  ✦  Said it anyway                          │
│     Tried a level above where you were.     │
│     Earned on 12 July.                      │
│                                             │
│  ○  In your own words                       │
│     Practise telling someone what helps     │
│     you at work.                            │
│     Not earned yet.                         │
└─────────────────────────────────────────────┘
```

Rules:

- **Text first, art second.** Badge art alone excludes P1 entirely. Every badge is a sentence
  before it is a graphic
- Unearned badges are shown at **full contrast** with the word "Not earned yet" — never greyed
  out. Greying makes the page read as a list of failures, and greyed text usually fails contrast
  anyway
- No countdown, no "2 more to go!" nudge. The condition is stated; the learner decides

### Awarding

A badge earned during a level appears **in the celebration sequence**, with its earned message
read as part of the single announcement:

> *"Level finished. Three stars. Forty XP. You tried a level above where you were."*

Never a separate interrupting popup.

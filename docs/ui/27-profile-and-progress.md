# 27 · Profile and progress

---

## 1. What Duolingo does

Avatar, display name, join date, then a stats row (streak · total XP · current league · top-3
finishes), an achievements grid, a friends list, and a following/followers count.

The profile is **public by default** and is the surface other learners see.

---

## 2. Why it works

- **One page answers "how am I doing"** without navigating.
- **The stats row is four glanceable numbers**, all rising.
- **Achievements give the page a horizon** — visible things still to reach.
- **Public visibility drives social accountability**, which is the strongest retention force
  available.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Public by default | Practice patterns, session length and modality use are inferable. In a special school where learners follow each other, this is an unconsented disclosure of disability |
| League shown as a headline stat | Rank as identity |
| Streak as a headline stat | A number that can fall, presented as who you are |
| No sense of *what you can now do* | Everything is volume — XP, days, rank. Nothing says "you can now ask for help" |

That last one is the real gap. The page measures activity, not capability.

---

## 4. SAMVAAD specification

### `/me` is private. There is no public profile.

No following, no followers, no visibility to any other learner. See file 23.

### The page answers three questions, in this order

**1 · What can I do now?** — the part Duolingo has no equivalent of, and the reason a learner
comes here.

```
┌────────────────────────────────────────────┐
│  Phrases you can rely on            47     │
│  You still know these weeks later.         │
│                                            │
│  Ready for                                 │
│  ✓ Asking someone to repeat                │
│  ✓ Saying you have finished                │
│  ✓ Asking for what you need                │
└────────────────────────────────────────────┘
```

Drawn from FSRS stability past the reliability threshold. **Capability, stated as capability** —
not as a count of lessons.

**2 · Am I better than I was?** — the PPI chart with the baseline drawn as a dashed line.

```
   ╭──────── you
  ╱
 ╱ ─ ─ ─ ─ ─ ─  where you started

 You are above where you started.
```

Baseline-relative, never compared to a non-disabled reference speaker (ADR-0003). Crossing the
dashed line is the emotional payoff of the whole product.

**3 · What have I kept doing?** — days practised, level, badges.

```
🔥 46 days practised · 6 in a row · longest 21
⭐ Level 4 · 340 XP
🪙 120
```

Note the order: **days practised** leads, because it can only rise. The current run is secondary
and never framed as at risk.

### Recommendations, never predictions

> **Try next:** *"Could you say that again, please?"* — you found this hard last week.

Every suggestion carries a reason the learner can read. There is **no predicted score, no
predicted date, no predicted ceiling** — for the learner, the trainer or the institution
(ADR-0011). A predicted ceiling shown to a disabled learner is a self-fulfilling prophecy with a
progress bar attached.

### Avatar

Learner avatar, editable, with mobility and communication aids as **ordinary options alongside
hats and shirts** — never a separate category. See file 21.

### Data and settings are one tap away

`/me/data` (export and erasure) and `/me/settings` are linked from here, prominently. A right the
learner cannot find is a right they have to email somebody about.

### Empty state

A new learner sees no zeroes. Instead:

> *"This fills up as you practise. Come back after a few sessions and you will see what you can
> rely on."*

A page of zeroes is a page that says *you have done nothing*, which is a poor first impression
for a product about capability.

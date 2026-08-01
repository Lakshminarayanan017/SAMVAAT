# 23 · Leagues, leaderboards and social

**The second pattern we refuse.** Recorded so it is not reintroduced later as "leagues",
"tournaments", "clubs" or "friends".

---

## 1. What Duolingo does

### Ten leagues, weekly cycles

Bronze → Silver → Gold → Sapphire → Ruby → Emerald → Amethyst → Pearl → Obsidian → Diamond.

30 learners per league, ranked by XP earned that week. **Top 7 promote. Bottom 5 demote.**

### The table is live

Positions shift in real time as other people practise. A learner can watch themselves drop.

### Friends

Follow other learners; see their streak, XP and league. Friend quests pair you with someone.

### Profile is public by default

Streak, total XP, league, achievements, join date — visible to anyone who follows you.

---

## 2. Why it works

Social comparison is the strongest retention mechanic available, full stop. It works because:

- **Rank is legible.** "14th, 3 places from demotion" is an instantly understood goal
- **The threat is specific and dated.** Demotion happens Sunday night
- **Other people's activity creates urgency** the product itself cannot manufacture
- **Promotion feels earned** because somebody else did not get it

Note the shape: it works by **threat and comparison**. Same family as hearts and streak-reset.

---

## 3. Why it is unacceptable here

| Consequence | Detail |
|---|---|
| **Ranks disabled people against each other by output** | A learner with a motor impairment composing on a switch produces less XP per hour than a fast typist. The league would rank them lower — and would be measuring their impairment, precisely and publicly |
| **Demotion is a public failure** | Delivered weekly, to a population disproportionately likely to have been failed publicly before |
| **It rewards volume, not learning** | The optimal league strategy is grinding easy content. That is directly opposed to spaced repetition |
| **It punishes an absence** | A hospital week means demotion |
| **Public profiles leak disability information** | Modality use, session length and practice patterns are inferable. In a special school or skilling centre where learners follow each other, a profile is a disclosure the learner never consented to |

That last point is the one that would still be disqualifying even if every other objection were
solved. Our product knows things about a learner that a language app does not.

**The brief itself said "no public leaderboards", the Ethics Charter agrees, a passing test
enforces it, and it was signed off as ADR/blueprint §2.9.** This file exists because "leagues"
and "tournaments" are the names it would come back under.

---

## 4. SAMVAAD specification

### Nothing compares one learner to another

- No leagues
- No leaderboards
- No ranks
- No public profiles
- No following, friends or followers
- No shared quests
- No visible activity of any other learner, anywhere

A learner cannot discover that another learner exists.

### What replaces it

Comparison is a real motivator and we do not have to give it up — we have to change the reference
point from *other people* to *your own past*.

**The Personal Progress Index already does exactly this.** It measures a learner against their own
rolling baseline, and it has two fairness gates in CI: monotonicity (a learner who improves sees
their number rise) and disfluency invariance (two learners improving identically, one with a
constant disfluency offset, get statistically indistinguishable trajectories).

```
┌──────────────────────────────────────────┐
│  You, over 8 weeks                       │
│                                          │
│   ╭──────── your line                    │
│  ╱                                       │
│ ╱  ─ ─ ─ ─ ─ ─ ─  where you started      │
│                                          │
│  You are above where you started.        │
└──────────────────────────────────────────┘
```

The baseline is drawn as a dashed line. Crossing it is the emotional payoff — *"I am better than
I was"* — and it is a comparison against a reference the learner cannot lose to, because it is
their own past.

### Tournaments against the AI are permitted

Explicitly allowed by the blueprint and worth keeping: a timed-**free** challenge against a
scripted opponent gives the *feel* of competition with none of the harm. Nobody is ranked, nobody
is demoted, and nobody's disability is measured against anyone else's.

Still no timer. The "challenge" is difficulty and variety, never speed.

### Trainers and institutions see aggregates, never comparisons

A trainer sees their own caseload, by name, **only for learners who granted them visibility**.
They never see a ranking.

An institution sees anonymised aggregates behind a k-anonymity floor of 5 — where a figure is
withheld if the cell *or its complement* is below the floor, because published figures can
otherwise be subtracted to recover a hidden one.

Neither surface ever ranks learners against each other. Not even privately, not even for staff.

### The test

`tests/no-comparison` asserts that no learner-facing response contains another learner's
identifier, and that no user-facing string in the reward system contains the words *rank*,
*league*, *leaderboard*, *position*, *demote*, *promote*, or *beat*.

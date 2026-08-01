# 18 · XP and levels

---

## 1. What Duolingo does

### XP is earned for completing things

~10 XP per lesson, ~20 for a story, bonus for perfect lessons, double-XP boosts from ads or
purchases. It appears in the header, the completion screen, the league table and the profile.

### XP drives three separate systems

1. **Leagues** — weekly competitive ranking
2. **Daily goal** — a target in XP (e.g. 20 XP/day)
3. **Course level** — a slowly-increasing number on the profile

### The XP number counts up on the completion screen

### Perfect-lesson bonus

Finishing with no mistakes earns extra XP.

---

## 2. Why it works

- **One number for all effort** is legible. A learner never has to work out which currency
  matters.
- **Counting up** makes it feel earned.
- **Feeding several systems** means every session advances multiple things at once, so progress
  feels dense.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Perfect-lesson bonus** | XP now depends on correctness. A learner having a bad day is penalised *twice* — once by the spaced-repetition schedule, once by reduced XP |
| XP feeds leagues | Ties effort to public ranking |
| Daily goal in XP | XP varies by exercise type, so a goal in XP is really a goal in "do more of the fast ones" |
| Double-XP purchases | Money buys progress |

---

## 4. SAMVAAD specification

### XP is for effort and **cannot see correctness**

This is enforced by function signature: `award_xp(attempt)` takes no `correct` flag. It is not a
policy someone can forget — it is not available to be got wrong.

Two reasons:

1. **Effort is the behaviour that produces learning.** Attempting a hard phrase and getting it
   wrong is more valuable than getting an easy one right.
2. **Scoring correctness twice doubles the penalty for a bad day.** FSRS already reschedules a
   missed phrase. Reducing XP as well punishes the same event a second time.

A learner who attempts a hard phrase and gets it wrong earns the same as one who got it right.

### What XP is worth

| Action | XP |
|---|---|
| Mission attempted | 5 |
| Level finished | 15 |
| Stretch bonus — attempting a level above your current one | +5 |
| Story finished | 15 |
| Interview finished | 25 |

**The stretch bonus is for attempting, not succeeding.** That is the point of it: it pays for
courage, which is the behaviour hardest to sustain and most worth rewarding here.

### XP buys nothing

There is no XP shop. XP is a record of effort, not a currency. It feeds:

- the **level** on the profile (a slowly-rising number, purely a record)
- the **daily goal**, which is derived from the learner's own `session_length_target_min`
- nothing else

**It does not feed a league, because there is no league.**

### The daily goal is the learner's own

Derived from the session length they chose during onboarding — 4 to 8 minutes depending on
profile — not a fixed number everyone competes against.

Missing it produces **nothing**. No red, no zero, no "you missed", no notification. The ring
simply is not full, and tomorrow it starts again.

### Levels

A level is `floor(sqrt(total_xp / 50)) + 1` — slow, always rising, never resetting. It is
displayed as `Level 4` with a progress bar to the next.

It is a record of accumulated effort. It unlocks nothing, gates nothing, and is compared to
nobody.

### Presentation

- Header: `⭐ 340` with `aria-label="340 XP"` — never a bare number
- Completion: counts up over ≤420ms with `tabular-nums` so it does not jitter
- Profile: total, level, and a bar to the next level

### What is never built

- No double-XP boosts
- No purchasable XP
- No XP decay
- No XP penalty of any kind
- No XP leaderboard

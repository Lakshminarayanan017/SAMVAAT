# 25 · Progression psychology

Why any of this works. The synthesis file for everything in 18–24.

---

## 1. What Duolingo does

### The four mechanics that actually drive engagement

Not the graphics. In order of importance:

1. **The session is short and its end is visible.** You always know how much is left.
2. **Something is always in motion.** A number, a bar, a crown, a streak. Progress is never
   invisible and never delayed.
3. **The next action is chosen for you.** No decision, so no friction before starting.
4. **Ending is rewarded, not starting.** The celebration is at the end of the unit of work, which
   is what makes finishing feel better than starting.

None of the four requires a mascot, particles, or a winding path.

### The three mechanics that drive *retention* — by threat

5. **Streak reset** — loss aversion
6. **Hearts** — scarcity and a paywall
7. **League demotion** — social threat

### Variable rewards

Chests give a random amount. Well-established as a stronger habit former than fixed rewards, and
the same mechanism as a slot machine.

### The onboarding hook

A learner completes a lesson **before** being asked to sign up. Commitment is obtained after the
first success, not before.

---

## 2. Why it works

Mechanics 1–4 work by **momentum**: they lower the cost of starting and raise the payoff of
finishing. They are the reason a session happens.

Mechanics 5–7 work by **threat**: they raise the cost of *not* returning. They are the reason
tomorrow happens.

Threat-based retention is genuinely more powerful. It is also why people describe the app in the
language of obligation — the owl meme exists because the mechanic is real.

---

## 3. Where it fails our learners

The distinction between momentum and threat is the entire analysis.

| | Works by | Our learners |
|---|---|---|
| Short session, visible end | Momentum | **Keep.** Especially valuable with fatigue and attention difficulties |
| Always something moving | Momentum | **Keep.** Progress that is invisible is progress that does not motivate |
| Next action chosen | Momentum | **Keep.** Removes decision load, which is a real barrier for several profiles |
| Reward the ending | Momentum | **Keep.** And make stopping feel equally fine |
| Streak reset | Threat | **Refuse.** Punishes illness |
| Hearts | Threat | **Refuse.** Punishes difficulty |
| League demotion | Threat | **Refuse.** Ranks disability |
| Variable rewards | Compulsion | **Refuse.** Aimed at cognitive and impulse-control differences |

A general-population product can use threat because a missed day is usually a choice. For our
learners a missed day is frequently **not a choice** — a fatigue crash, a seizure, a hospital
admission, an unavailable carer, a bad pain week. Punishing it is punishing the disability.

---

## 4. SAMVAAD specification

### The bet

> **Momentum, not fear.**

We take all four momentum mechanics, refuse all three threat mechanics, and accept that retention
will be somewhat lower than a threat-based design would produce.

That is a real cost, stated plainly. It buys a product that a learner who has been failed by
systems before can use without being failed again — which is the only version of this product
worth building.

### The four, implemented

| Mechanic | Where it lives |
|---|---|
| **Short session, visible end** | 3–6 missions, 3–7 minutes. `ProgressDots` states "3 of 6 done" in words on every mission. Mission count fixed at the start so it can never grow |
| **Always in motion** | XP counts up, stars land, the daily ring fills, the PPI line moves. Every one of them is also present as text, so motion emphasises rather than carries |
| **Next chosen for you** | Home resolves to a specific level. `Continue` goes somewhere specific. Browsing available, never required |
| **Reward the ending** | Celebration at level end only, never per mission. `Done for today` is equal weight to `One more` |

### What we add that Duolingo does not have

**The third star requires returning.** One star for finishing, two for accuracy, and the third
only when FSRS stability shows the phrase is *still held* weeks later.

This is the honest version of a retention mechanic: the product's central claim is that learning
sticks, so the top reward is proof that it stuck. It cannot be earned in one sitting, it cannot
be ground out, and it rewards exactly the behaviour that produces real learning.

It is also, unlike a streak, impossible to lose.

**The baseline crossing.** At around week four, the PPI chart shows the learner above their own
starting line. *"I am better than I was."* Not better than anyone. This is the emotional payoff
the whole product is built toward, and it needs no comparison to another person.

### The emotional arc we are designing for

| When | The beat |
|---|---|
| Day 0, +0s | *"This was built for me, not adapted for me."* |
| Day 0, +2min | *"I did that."* — a completed mission before any account or form |
| Day 0, +5min | *"That is where this goes, and it is for me."* — seeing World 10 is The Interview, and unlocked |
| Day 1 | *"Something is waiting for me."* — never *"I let something down"* |
| Week 2 | *"It stuck. I actually learned this."* — the third star |
| Week 4 | *"I am better than I was."* — the baseline crossing |
| Week 8 | *"I have said this out loud before. I can say it again."* |
| Week 12 | *"I was judged on what I said."* — the interview. For many learners, the first time |

Every design decision is checkable against that arc. **If a feature does not advance one of those
beats, it is decoration.**

### The rule that governs all of it

> **Nothing may punish an absence, a mistake, or a slowness.**

Absence → no streak reset, no missed-day record, no guilt notification.
Mistake → no hearts, no lives, no accuracy badge, no XP penalty.
Slowness → no timer, no speed bonus, no "Speedy" tile, no response-time measurement.

Each has a file explaining what replaces it, and each has a test.

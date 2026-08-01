# 20 · Hearts and failure walls

**The pattern we refuse.** This file exists so nobody reintroduces it later under a different
name, and so the replacement is specified rather than merely absent.

---

## 1. What Duolingo does

### Five hearts

Displayed in the lesson chrome. **Each wrong answer costs one.** At zero, the lesson ends and the
learner cannot start another.

### Getting hearts back

| Route | Cost |
|---|---|
| Wait | ~4–5 hours per heart |
| Practice session | One heart for a full review |
| Gems | Currency, earned slowly or bought |
| Super subscription | Unlimited hearts |

### The heart is visible at all times during a lesson

A dwindling resource in the corner of every question.

---

## 2. Why it works — commercially

Hearts are, straightforwardly, the monetisation engine. The sequence is designed:

1. A learner makes mistakes — which is what learning *is*
2. They hit a wall mid-session, at the point of maximum engagement
3. The wall offers three exits: wait, grind, or pay
4. Unlimited hearts is the headline feature of the subscription

It also has a genuine pedagogical veneer: scarcity increases care, and the wall prevents mindless
tapping.

**But note what the mechanic actually measures.** Hearts do not cost you for going too fast, or
for guessing. They cost you for being **wrong**. And the learner who is wrong most often is the
learner who most needs the practice.

---

## 3. Why it is unacceptable here

| Consequence | Who it hits |
|---|---|
| A learner who makes more mistakes gets **less** practice | Exactly inverted. The learner with an intellectual disability or aphasia is the one who runs out first |
| The wall arrives mid-session, at peak engagement | Maximum frustration by design |
| "Pay to continue learning" | Charging a disabled person for the privilege of practising more |
| A visible dwindling resource during every question | Adds anxiety to every attempt, for a population with elevated baseline anxiety |
| ASR mis-scoring costs a heart | An atypical-speech learner loses hearts to the *recogniser's* failure, not their own |

**Ethics E7:** a feature that fails a persona is not shippable. Hearts fail P4 (intellectual
disability) and the aphasia profile immediately, structurally, and by design.

There is no version of hearts we can ship. Not a gentler version, not more hearts, not slower
regeneration. The mechanic's function is to convert difficulty into a wall, and difficulty is
what our learners have.

---

## 4. SAMVAAD specification

### There are no hearts, lives, energy, or any consumable

Asserted by test: no user-facing string in the reward system mentions losing anything, and no
learner state has a depletable field.

### What replaces the slot they occupied

Hearts genuinely do three jobs. Each needs a non-punishing replacement, or the loop goes slack.

| Heart's job | Our replacement |
|---|---|
| **Makes attempts feel like they matter** | Stars. Earned for mastery, and the third requires *returning*. Something is at stake — a reward not yet earned, rather than a resource being drained |
| **Prevents mindless tapping** | Coaching that names what does fit. A learner who taps randomly gets told the answer each time and learns nothing; nothing punishes them, and the phrase simply comes back tomorrow via FSRS |
| **Creates a session boundary** | The daily goal, derived from the learner's own session length. A soft, additive end — "you've done what you planned" — rather than a hard wall |

The difference in one line: **hearts make you stop because you failed. A daily goal makes you
stop because you finished.**

### What the learner sees instead of a heart counter

Nothing. The lesson chrome is `[ Leave ]  ●●●○○  3 of 6 done`. There is no third element, because
there is nothing to count down.

### The mistake budget is infinite, and this is stated

The level intro says it plainly:

> *"You can stop at any time, and nothing is timed."*

And the first-run onboarding says it once, explicitly:

> *"You can get things wrong as many times as you like. Nothing is ever taken away."*

Worth saying out loud, because a learner arriving from any other learning app **assumes** there
is a limit, and that assumption changes how they attempt things.

### Guarding against reintroduction

Three defences, in increasing order of usefulness:

1. This document
2. A test asserting no reward-system string mentions losing, running out, or refilling
3. **A named function that refuses.** As with `days_until_streak_at_risk()`, if anybody adds a
   heart system the natural entry point exists and returns nothing, with the reason attached —
   so the refusal is found at the moment somebody goes looking for the feature

### The general rule this file is an instance of

> **No mechanic may punish an absence, a mistake, or a slowness.**

Hearts punish mistakes. Streak resets punish absence. Timers punish slowness. All three are
refused, and each has a file explaining what replaces it.

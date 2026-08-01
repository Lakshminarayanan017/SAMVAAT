# 13 · Lesson flow — open to complete

The core loop. If this screen is right, the product works.

---

## 1. What Duolingo does

### The whole flow

```
tap node → popover → START
  ↓
[ lesson chrome appears, all navigation gone ]
  ↓
question 1 → answer → CHECK → feedback banner → CONTINUE
question 2 → …
  ↓
(wrong answers are re-queued to the end)
  ↓
completion sequence → stats → CONTINUE
  ↓
back to path, node now complete
```

### The chrome, fixed for the whole lesson

```
[×]   ▓▓▓▓▓▓▓░░░░░░░░░   ♥5
```

Close, progress bar, hearts. Nothing else. The bar fills per question answered.

### Answer area, then a fixed bottom CTA

Question at the top. Answer options in the middle. **CHECK** anchored to the bottom, disabled and
grey until an answer is selected.

The button never moves. Across a whole lesson the learner's thumb returns to exactly the same
place.

### Wrong answers are re-queued

A missed question comes back at the end of the lesson. The lesson is not over until everything
has been answered correctly at least once.

### Closing mid-lesson warns

"Are you sure? You'll lose your progress." Progress in that lesson is genuinely discarded.

---

## 2. Why it works

- **Removing all navigation** converts a page into a task. It is the single biggest reason a
  lesson feels like a game.
- **The progress bar is a contract.** The learner can always answer "how much is left".
- **A fixed CTA position** becomes motor memory within one lesson.
- **Disabled-until-answered** removes the possibility of a wasted tap and communicates "choose
  something" without copy.
- **Re-queueing** guarantees the learner leaves having got everything right at least once, which
  is a much better closing feeling than "you got 7/10".

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Hearts in the chrome | A visible dwindling resource. Reaching zero ends the session — a wall for exactly the learner who needs the practice |
| "You'll lose your progress" on exit | Coercion. A learner with a fatigue condition, an attention difficulty, or an unexpected interruption is punished for stopping |
| Progress genuinely discarded | Compounds the above |
| Re-queueing has no cap | A learner having a hard day can be held in a lesson indefinitely. Intended as thoroughness, experienced as being unable to leave |
| No pause / resume | Sessions must be completed in one sitting |
| A single progress bar for a variable-length lesson | Re-queueing makes the total grow, so the bar can move *backwards* |

---

## 4. SAMVAAD specification

### The flow

```
level row → level opens directly (no popover)
  ↓
INTRO      what this is · how many missions · skippable
  ↓
MISSION    one question, one screen
  ↓        answer → feedback → Next
  ↓        (repeat, 3–6 times)
  ↓
CELEBRATION  stars land · XP counts · one announcement
  ↓
"One more"  |  "Done for today"      ← equal weight
```

### The chrome

```
[ Leave ]   ●●●○○○   3 of 6 done
```

Three elements. **No hearts, because there are none.**

- **Leave** is a labelled button, not a bare ×. An unlabelled × is ambiguous for a learner with
  an intellectual disability
- Progress is **dots plus the sentence "3 of 6 done"**. The sentence is the accessible name; the
  dots are decoration over it
- The mission count is **fixed at the start** and cannot grow, so the indicator never moves
  backwards

### The intro

```
World 2 · Making Sure You Understand
Asking someone to repeat

4 things to try.
You can stop at any time, and nothing is timed.

[ Start ]        [ Not now ]
```

Eight seconds of reading, skippable, and never shown twice for the same level. It exists to make
the end visible **before the beginning**, and to state the two guarantees that matter most up
front: you can stop, and nothing is timed.

### One mission per screen

```
┌────────────────────────────────────────┐
│ [ Leave ]      ●●○○   2 of 4 done      │
├────────────────────────────────────────┤
│                                        │
│  Which one fits here?                  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ [ the phrase, via modality       │  │  ← ContentBlock through
│  │   router: text / audio / symbols │  │    the router. Arrives as
│  │   / Easy-Read / ISL ]            │  │    whatever the learner reads
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Could you say that again?       │  │  ← options, ≥--target-min
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │  I have finished that task.      │  │
│  └──────────────────────────────────┘  │
│                                        │
│  [ Give me a hint ]                    │  ← always present
│                                        │
├────────────────────────────────────────┤
│  ( feedback appears here )             │
└────────────────────────────────────────┘
```

### There is no CHECK button

Selecting an option **is** the answer. Duolingo's two-step (select, then CHECK) exists to allow
changing your mind before committing — reasonable when a wrong answer costs a heart.

Nothing costs anything here, so the second step is pure friction: one extra tap per question, or
one extra full scan cycle for a switch user, per question, forever.

Production missions, which have no options, keep an explicit two-button answer because there is
nothing to select.

### Leaving is free and never warned

```
[ Leave ]  →  leaves. Immediately.
```

No confirmation, no "are you sure", no warning about losing progress. Every mission answered is
already recorded — the outbox sends it, offline or not.

A product for people with fatigue conditions that makes stopping feel like quitting is a product
that punishes fatigue.

### Wrong answers are not re-queued

The mission shows coaching, names what does fit, and the learner presses Next. The phrase returns
**tomorrow**, scheduled by FSRS, which is a better instrument than re-queueing:

- it schedules by actual forgetting, not by "you missed it four minutes ago"
- it cannot hold a learner in a lesson they want to leave
- it keeps the mission count fixed, so progress never moves backwards

### Unlimited retries at no cost

No hearts, no lives, no energy, no penalty. A learner may answer, see the coaching, and continue.
There is nothing to run out of.

### A scaffold on every mission

`Give me a hint` is present on every mission at every point. Requesting it lowers the **FSRS
grade** — genuine partial recall — and never lowers **XP**, which is for effort. Both are enforced
in the API by function signature, so the client only reports what happened.

A mission with no way to ask for help is a mission a learner can get stuck in, and getting stuck
with no exit is how somebody decides the app is not for them.

### Nothing is timed

No countdown, no speed bonus, no "you took a while". Ethics E6. Tested by reading the rendered
output rather than the source, so copy added later is covered.

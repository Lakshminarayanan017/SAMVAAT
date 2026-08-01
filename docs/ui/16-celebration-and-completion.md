# 16 · Celebration and lesson completion

The payoff. The reason finishing feels better than starting.

---

## 1. What Duolingo does

### A staged sequence, not a screen

```
1  full-screen wash + character + confetti      ~1.2s
2  "Lesson complete!"                           slides in
3  three stat tiles, one at a time, ~150ms apart
      TOTAL XP  |  SPEEDY  |  GOOD
      15        |  1:42    |  92%
   each counts up from zero
4  CONTINUE
```

### The stats

| Tile | Meaning |
|---|---|
| Total XP | Effort earned |
| Speedy | How fast — a **timing** metric |
| Good / Amazing | Accuracy percentage |

### Milestone celebrations are bigger

Finishing a unit, hitting a streak day, levelling a crown each get their own larger sequence with
more animation.

### The character reacts

Duo appears celebrating.

### Sound

A short fanfare, and rising ticks under each counting number.

---

## 2. Why it works

- **Staging is the entire trick.** The same three numbers shown at once take 300ms and feel like
  data. Revealed one at a time over ~2s, they feel like a ceremony.
- **Counting up** converts an assignment into an event. The number *arriving over time* is what
  makes it feel earned.
- **Celebrating the end, not the start**, is what makes finishing worth doing. Celebrating every
  correct answer would devalue the currency and lengthen the session by ~40%.
- **The ceremony is short.** Under three seconds. Long enough to feel like something, short enough
  not to be in the way by session ten.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **A "Speedy" tile** | A timing metric, celebrated. Directly punishes motor impairment, AAC composition, and stammering. Ethics E6 forbids it outright |
| **An accuracy percentage** | On a bad day, "40%" is the last thing on screen. A learner told they are 40% has been given a verdict, not a reward |
| Full-screen confetti, ~1.5–2s | Worst pattern for vestibular sensitivity. Nausea closes the app permanently |
| ~2–3s total | A switch-scanning learner waits it out before the next scan step is safe — on every lesson, forever |
| Each stat animating in separately | Three live-region updates; a screen reader reads three interruptions, the last two cutting off the first |
| Escalating praise headline | Becomes conspicuous when it stops |

---

## 4. SAMVAAD specification

### The sequence

```
1  card lifts in                                  240ms
2  "Level finished"
3  stars land, one at a time                      130ms stagger
4  XP counts up                                   ≤420ms
5  badge, if one was earned
6  [ One more ]   [ Done for today ]
```

**Total ≤ 900ms.** Ceiling on any single animation is 420ms.

### The three tiles are replaced

| Duolingo | SAMVAAD | Why |
|---|---|---|
| Total XP | **XP earned** | Kept. Effort-based and cannot see correctness |
| Speedy (time) | **removed entirely** | Timing. Ethics E6 |
| Good (accuracy %) | **Stars** | A star is a threshold, not a percentage. "2 of 3 stars" on a bad day is an achievement; "58%" is a verdict |

Nothing on this screen is a percentage of the learner.

### Announced once, as one complete sentence

> *"Level finished. Two stars. Forty XP."*

Fired **after** the animation, `role="status"`, once.

The obvious implementation fires a live-region update per element as it appears. A screen reader
then reads three interruptions with the last two cutting off the first, and the learner hears
nothing complete. This is the single easiest thing to get wrong on this screen.

### Three motion levels

| Level | Behaviour |
|---|---|
| **Full** | Stars land with a spring; a bounded particle burst on 3 stars — **≤24 particles, single emission, no loop, not full-screen** |
| **Gentle** *(default)* | Stars land with a 130ms stagger; XP counts. No particles |
| **Still** | Everything present immediately; a short cross-fade only |

`prefers-reduced-motion` resolves to Still unless the learner has chosen otherwise in-app.

**Every figure is on screen as text regardless of level.** Remove all motion and the screen says
exactly the same things — that is the rule, and it is tested.

### "Done for today" is a first-class action

```
[ One more ]        [ Done for today ]
```

Equal visual weight. Same element type, same size, same prominence. Never smaller, never grey,
never a text link under the real button.

A product for people with fatigue conditions that makes stopping feel like quitting is a product
that punishes fatigue. This is one of the clearest places where our psychology diverges from the
source, and it is deliberate.

### No streak pressure anywhere on this screen

No "keep your streak alive", no "come back tomorrow", no countdown to anything. If a streak was
extended, it is stated as a fact — *"6 days practised."* — and never as something now at risk.

### Mitra appears, once

Delighted state, single animation, `aria-hidden`, absent under Still. The message is in the text
beside the bird; Mitra never carries information alone.

### Badges

If one was earned, it appears in the sequence with its **text label and earned message**. Badge
art alone excludes P1 entirely, so every badge is a sentence first and a graphic second.

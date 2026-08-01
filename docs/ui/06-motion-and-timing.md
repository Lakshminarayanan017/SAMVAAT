# 06 · Motion and timing

---

## 1. What Duolingo does

### Motion is everywhere and it is fast

| Moment | Approx duration |
|---|---|
| Button press | ~80ms |
| Answer card select | ~120ms |
| Progress bar fill | ~300ms, ease-out |
| Feedback banner slide up | ~200ms |
| Screen push transition | ~250ms |
| Node bounce (idle, looping) | ~1.2s cycle |
| Stat count-up | ~600–900ms |
| Lesson-complete confetti | ~1.5–2s |

### The active node breathes

The next lesson node has a slow looping scale animation. It is the only looping animation in the
main interface, and it is doing one job: drawing the eye to the single thing you should press.

### Numbers count rather than appear

XP, streak and accuracy on the completion screen animate from 0 to their value. The number
arriving *over time* is what makes it feel earned rather than assigned.

### Choreography, not simultaneity

The completion screen does not show three stats at once. Each slides in and counts, one after
another, ~150ms apart. The staging is what makes it feel like a ceremony.

### The character reacts

The mascot animates on correct answers and at lesson end. It is decorative and never blocks.

---

## 2. Why it works

- **Fast interaction motion (<150ms)** reads as responsiveness. Slower reads as lag.
- **The breathing node** replaces a written instruction. No copy needed for "press here".
- **Counting numbers** convert an assignment into an event. The same number shown statically
  feels like data; counted, it feels like a reward.
- **Staging** stretches a 3-second moment into something that reads as a sequence with a
  beginning and an end — which is what makes finishing feel better than starting.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Looping node animation | A permanently moving object on a screen someone with an attention difficulty is trying to read |
| Confetti at 1.5–2s, full screen, many particles | The worst possible pattern for vestibular sensitivity. Nausea closes the app permanently |
| Long celebration | A switch-scanning learner waits out every animation before the next scan step is safe. A 2s celebration costs them 2s on every lesson, forever |
| `prefers-reduced-motion` treated as all-or-nothing | Reduced usually means "no animation at all", which removes the *signal that something changed* — real information for a learner with a cognitive disability |
| Animation carrying information | If the only indication a lesson unlocked is a bounce, a learner with animation off never learns it unlocked |

---

## 4. SAMVAAD specification

### The rule that makes motion safe

> **Animation may only emphasise something that is already true in the DOM.**

Remove every animation and the app must be completely usable and say exactly the same things.
This is a test, not an aspiration: `tests/motion-removal` renders every screen with motion
disabled and asserts the accessible text is identical.

### Durations

| Token | ms | Use |
|---|---|---|
| `--t-instant` | 90 | Press, hover, focus |
| `--t-quick` | 160 | Selection, chip, tooltip |
| `--t-base` | 240 | Panel, route change, banner |
| `--t-celebrate` | 420 | **Ceiling anywhere in the product** |

**420ms is a hard ceiling.** A switch-scanning learner waits out every animation before the next
scan step is safe to read. This is the single most important number in this file.

### Curves

| Token | Value | Use |
|---|---|---|
| `--e-enter` | `cubic-bezier(.16,1,.3,1)` | Arriving; decelerates and settles |
| `--e-exit` | `cubic-bezier(.4,0,1,1)` | Leaving; accelerates away |
| `--e-standard` | `cubic-bezier(.4,0,.2,1)` | Anything that moves and stays |
| `--e-spring` | `cubic-bezier(.34,1.56,.64,1)` | One controlled overshoot. Rewards only |

A real physics spring is deliberately avoided: it has no fixed duration, and an animation whose
end cannot be predicted is one a screen-reader announcement cannot be sequenced after.

### Three motion levels

| Level | Behaviour |
|---|---|
| **Full** | Everything, including a bounded particle burst on a level completion |
| **Gentle** *(default)* | Transforms and fades. Stars land, numbers count. No particles, no parallax, no loops |
| **Still** | Opacity only |

`prefers-reduced-motion: reduce` resolves to **Still** — unless the learner has explicitly chosen
otherwise in the app. The OS is a default, not a verdict: someone who set it months ago for a
different app must be able to turn motion back on here.

### Reduced motion keeps cross-fades

Still returns a short opacity transition, **not `none`**. A hard cut loses the signal that
something changed, and that signal is doing real work for a learner with a cognitive disability.
The change simply must not travel through space.

### Particles

Full level only. **≤24, single emission, no loop, not full-screen.** Bounded by construction, not
by configuration.

### No looping animation anywhere

The "press here" job that Duolingo's breathing node does is handled by **size, position, fill and
the word `Continue`** instead. A permanently moving element is a permanent distraction, and there
is no reduced-motion setting that makes a loop acceptable for the learner who needs to read past
it.

### Announcement sequencing

A celebration is announced **once, as one complete sentence, after the animation** —
*"Level finished. Two stars. Forty XP."*

The obvious implementation fires a live-region update per element, which a screen reader reads as
three interruptions with the last two cutting off the first.

### Performance

`transform` and `opacity` only. Never `width`, `height`, `top`, `left` or `box-shadow`.
`will-change` is applied at animation start and removed at the end. The target device is a
₹8,000 Android, profiled, not a development laptop.

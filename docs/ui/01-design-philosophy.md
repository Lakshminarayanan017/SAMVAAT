# 01 · Design philosophy

The five principles everything else in this folder derives from.

---

## 1. What Duolingo does

### The interface has almost no chrome

Open the app and you are looking at **one thing**: a vertical path with one obviously-next node
on it. There is no dashboard, no summary, no "welcome back" card, no list of options. The header
is four small glanceable numbers. The bottom bar is five icons.

Everything else — settings, achievements, shop, friends — is one level down and out of the way.

### There is never a decision before starting

The next lesson is chosen. The button says START and it is attached to a specific node. A learner
who opens the app with no intention beyond "do my practice" can begin in one tap without
evaluating anything.

Choosing is possible (scroll and tap another node) but never required.

### The end is always visible

Inside a lesson, a progress bar fills. Outside, a unit shows "3/6". A learner can answer "how
much is left?" at every moment without asking anyone.

### Everything is one screen deep

One question per screen. One idea per card. No screen requires scrolling to understand what is
being asked. Answer options are always in the same place; the primary button is always
bottom-anchored in the same position.

Motor memory does the navigating after day three.

### Feedback is immediate, loud and in a fixed place

The answer banner slides up from the bottom edge, always the same size, always with the continue
button in the same spot. You never look for it.

---

## 2. Why it works

| Principle | The mechanism |
|---|---|
| **No chrome** | Every additional element on a screen is a decision the user has to make. Removing decisions removes friction, and friction at the start of a session is what determines whether the session happens |
| **Next action chosen** | Choice paralysis is the largest single drop-off point in any learning app. Removing the choice removes the drop-off |
| **Visible end** | People finish things whose end they can see. An open-ended session gets abandoned at the first interruption; a session with three dots left gets finished |
| **One screen deep** | Working memory is the constraint in learning, not screen space. Two things on a screen means the learner spends some of their attention deciding what to look at instead of answering |
| **Fixed feedback position** | After ~10 repetitions the learner stops reading the interface and only reads the content. That is the goal state |

The deepest one: **the loop is designed around returning, not around a single session.** Every
mechanic exists to make tomorrow more likely, not to make today longer.

---

## 3. Where it fails our learners

| Duolingo behaviour | Why it fails |
|---|---|
| Dense information in the top bar (4 counters, small type) | Illegible at low vision; a lot of unlabelled iconography for a screen-reader user |
| Colour-coded state everywhere (green = done, grey = locked) | Roughly 1 in 12 men has a colour vision deficiency. State must never be colour-only |
| Animation on almost everything, always on | Vestibular triggers, and a permanent distraction for an attention difficulty |
| Padlocks on locked content | A padlock on a product built for disabled people reads as "not for you" |
| The path encodes order in 2D position | Meaningless to a screen reader; a zig-zag is bad for row-column switch scanning; fails 400% reflow |
| Speed bonuses and timed challenges | Directly punishes motor impairment, AAC composition, and stammering |

---

## 4. SAMVAAD specification

### The five principles, as rules

**P1 · One primary action per screen.**
Every screen has exactly one visually dominant action. It is bottom-anchored on mobile,
full-width, and it is the only element using the brand fill. Secondary actions are present but
never compete.

**P2 · The end is always visible, in words.**
Every multi-step surface shows progress as **text plus a visual**, never a visual alone.
`"3 of 6 done"` is the accessible name; the dots are decoration over it.

**P3 · No decision before starting.**
Home resolves to a specific next level. The primary button is `Continue` and it goes somewhere
specific. Browsing is always available and never required.

**P4 · One idea per screen, in the learner's channel.**
A mission asks one thing. The thing is a `ContentBlock` rendered through the modality router,
so it arrives as text, speech, symbols, Easy-Read or ISL according to the profile — without the
screen branching.

**P5 · State is never carried by colour alone.**
Every state has three signals: colour, shape or icon, and text. A screen rendered in greyscale,
or in forced-colours mode, loses nothing.

### The rule that overrides the other five

> **Nothing may punish an absence.**

No hearts, no lives, no energy, no timers, no streak-at-risk warnings, no "you missed", no
locked content, no public comparison. Every mechanic is additive. A learner returning after three
weeks away finds everything they built still there and nothing scolding them.

This is not a softer version of Duolingo's psychology. It is a different bet: Duolingo uses
**loss aversion** because it works on a general population, and it works partly by making people
anxious. Our population is disproportionately likely to have been failed by systems that
punished them for things outside their control. Momentum, not fear.

### Quality bar

Before any screen is considered done:

- [ ] One primary action, unambiguous
- [ ] Progress or position stated in words
- [ ] Usable at 400% zoom with no horizontal scroll
- [ ] Usable with all animation disabled, saying exactly the same things
- [ ] Usable in greyscale
- [ ] Every interactive target ≥ the learner's configured minimum (44–88px)
- [ ] Nothing counts down; nothing warns about loss
- [ ] Reachable by keyboard, switch scan and screen reader
- [ ] Loading, empty, error and offline states designed, not defaulted

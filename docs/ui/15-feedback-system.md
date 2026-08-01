# 15 · The feedback system

The banner that appears after every answer. Duolingo's single best-executed component, and the
one whose copy we must change most.

---

## 1. What Duolingo does

### A banner slides up from the bottom edge

Fixed height (~140px), full width, sitting above the safe area. It contains an icon, a headline,
sometimes the correct answer, sometimes a "report" link, and the **CONTINUE** button.

### Correct

```
┌────────────────────────────────────────┐
│  ✓  Nice!                              │   green wash, green ink
│                                        │
│     ┌──────────────────────────────┐   │
│     │          CONTINUE            │   │   green button
│     └──────────────────────────────┘   │
└────────────────────────────────────────┘
```

Headline varies: "Nice!", "Correct!", "Amazing!", "You're on fire!"

### Incorrect

```
┌────────────────────────────────────────┐
│  ✗  Correct solution:                  │   red wash, red ink
│     Yo bebo agua                       │
│                                        │
│     ┌──────────────────────────────┐   │
│     │          CONTINUE            │   │   red button
│     └──────────────────────────────┘   │
└────────────────────────────────────────┘
```

### The CONTINUE button is in the same place as CHECK was

The button the learner just pressed is replaced *in situ* by the next one. No thumb movement
between answering and continuing.

### Sound and haptic fire simultaneously

### Timing

Banner slides in ~200ms. The learner can press CONTINUE immediately — nothing waits for the
animation.

---

## 2. Why it works

- **Fixed position and size** mean the learner never searches. After ten questions they are not
  reading the interface at all.
- **CONTINUE replacing CHECK in place** is the detail that makes a lesson feel fast. Two taps in
  the same spot per question.
- **Showing the correct answer on failure** is genuinely good pedagogy — a learner who does not
  learn what the answer was has gained nothing from getting it wrong.
- **The banner does not block** — it can be dismissed the instant it appears.
- **Peripheral colour tells you before you read.** You know the outcome before your eyes reach
  the text.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Red for wrong** | Red is an alarm colour. For a learner with communication anxiety, an alarm on a practice attempt is exactly the wrong signal. Also the worst possible pairing with green for the most common colour vision deficiency |
| **"✗"** | A cross is a verdict |
| **"Correct solution:"** | Implies what the learner produced was an *incorrect* solution. Framing |
| Escalating praise ("Amazing!", "You're on fire!") | Praise inflation. It also becomes conspicuous when it stops |
| Banner overlays content at large text sizes | The question being explained can be covered by the explanation |
| A `role="alert"` per banner | Interrupts a screen reader mid-sentence, every question |
| Audible failure buzz | Announces a wrong answer to the room |

---

## 4. SAMVAAD specification

### Two states, and neither is a verdict

**Accepted**

```
┌────────────────────────────────────────┐
│  ✓  That fits.                          │   --good-wash / --good-ink
│                                         │
│     [ Next ]                            │
└────────────────────────────────────────┘
```

**Not yet**

```
┌────────────────────────────────────────┐
│  →  Not quite yet.                      │   --try-wash / --try-ink  (amber)
│     The one that fits is:               │
│     "Could you say that again, please?" │
│                                         │
│     [ Next ]                            │
└────────────────────────────────────────┘
```

### The four copy rules

1. **Never the word "wrong", "incorrect", "failed" or "mistake".** Tested against rendered
   output, so copy added later is covered.
2. **Always name what does fit.** "Not quite" alone leaves the learner exactly where they were.
3. **No escalating praise.** "That fits." every time. Consistent, calm, and — importantly — it
   does not become conspicuous by its absence on a bad day.
4. **Never "solution".** The learner produced an attempt, not a wrong solution.

### The colour pairing is jade and amber, not green and red

| | Hue | Glyph | Word |
|---|---|---|---|
| Accepted | jade `--good-ink` | ✓ | "That fits." |
| Not yet | amber `--try-ink` | → | "Not quite yet." |

Three independent signals. Rendered in greyscale, the glyph and the words still carry it entirely.

Amber rather than red for two reasons: it is not the red-green pair that a deuteranope cannot
separate, and it is a **lower-arousal colour**. The feeling we want is "noted, carry on", not
"alarm".

The glyph is a **forward arrow**, not a cross. It points at what comes next.

### Layout

The banner is a **flex sibling of the scrolling content**, not an overlay. It cannot cover the
question it is explaining at any text size — a WCAG 2.4.11 failure removed by construction rather
than by tuning.

### Announcement

`role="status"` (polite), **not** `role="alert"`. One announcement, one sentence:

> *"Not quite yet. The one that fits is: Could you say that again, please?"*

Assertive interruption is for things that need immediate attention. A practice answer does not,
and interrupting a screen reader mid-sentence on every single question is exhausting.

### Focus moves to the banner

On appearance, focus moves to the banner heading. So:

- a screen-reader user hears it immediately, without hunting
- a keyboard user's next Tab reaches **Next**
- a switch user's scan starts at the banner rather than at the top of the document

The banner is `tabIndex={-1}` — programmatically focusable, not in the tab order.

### `Next` occupies the same position

Same place every time, so the learner's thumb, cursor or scan lands where it did last time. The
one Duolingo detail here worth copying exactly.

### Sound

Neutral tone for "not yet", **not** a buzz — and off by default. See file 08.

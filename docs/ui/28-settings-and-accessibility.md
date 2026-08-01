# 28 · Settings and accessibility

**The screen where our product must be best in class.** Duolingo's is a competent afterthought;
ours is a primary surface.

---

## 1. What Duolingo does

Settings is a list of toggles grouped under headings: sound effects, speaking exercises, listening
exercises, motivational messages, notifications, appearance (light/dark/system), and account.

Accessibility gets a small section — mainly the ability to disable speaking and listening
exercises.

Changes save immediately. Some require a restart.

---

## 2. Why it works

- **A flat list of toggles is instantly understood**, no hierarchy to learn.
- **Immediate save, no Save button** — no lost work.
- **Grouping under headings** makes a long list scannable.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Accessibility = "turn off the exercises you cannot do"** | The learner ends up with a smaller course than everyone else. This is the central failure |
| No text size control | Relies on OS settings, which many learners have never found |
| No contrast control beyond dark mode | Dark mode is not high contrast |
| No motion control | `prefers-reduced-motion` only, with no in-app override |
| No target size control | 44px for everybody |
| Settings buried under account | Several taps deep |
| Toggle labels assume vocabulary | "Listening exercises" means little to a learner who has never had one |

---

## 4. SAMVAAD specification

### It is called "How this app talks to me"

Not "Accessibility". Not "Settings". The name states its purpose in the learner's own terms, and
it removes the framing where accessibility is a special section for special users.

### It is a route, not a dialog

`/me/settings`. Reachable from anywhere including the browser's history, satisfying the charter
requirement of **≤2 actions from anywhere**. A dialog satisfies that on paper and fails it in
practice: it can only be opened from wherever its trigger lives, and a learner in a chrome-free
mission has no route to it.

### There is no Save button

Every change applies immediately and persists in the background.

A learner who cannot read the current contrast well enough to find Save **cannot save the setting
that would let them read it**. That is precisely the population this screen exists for.

A failed save says so without reverting what the learner can already see working:

> *"Your change is working now, but we could not save it for next time. We will keep trying."*

### What is controllable

| Group | Setting | Options |
|---|---|---|
| **Reading** | Text size and wording | Standard · Easy-Read |
| | Text scale | 100 · 125 · 150 · 200% |
| | Line spacing | Normal · Loose |
| **Seeing** | Contrast | Standard · High contrast |
| | Light or dark | Match my device · Light · Dark |
| **Moving** | Movement | Allow · Gentle · None |
| | Celebrations | Full · Gentle · Still |
| **Touching** | Button size | Standard 44 · Large 64 · Largest 88 |
| **Hearing** | Interface sounds | Off (default) · On |
| | Haptics | On (default) · Off |
| | Reading speed | Slow · Normal |
| **Channels** | How things are shown to me | Text · Audio · Symbols · Easy-Read · Sign |
| | How I answer | Typing · Speaking · Symbols · Switch · Sign |
| **Pace** | Session length | 4–12 minutes |
| **Profile** | Which preset | 16 options + "I would rather not say" |

Every one of these is a real, working control. None of them removes content.

### The rule that separates us from the source

> **No setting makes the course smaller.**

There is no "turn off speaking exercises", because there are no speaking exercises to turn off —
a mission arrives as a **modality-neutral `ContentBlock`** and the router renders it in the
learner's channel. A non-speaking learner gets the same mission as an AAC composition.

This is the single largest structural difference in the entire analysis. Duolingo makes exercises
accessible by letting you decline them; that yields a smaller course. We make the *content*
modality-neutral and choose the rendering at runtime, so everybody gets all of it.

### Changing a profile re-presets rather than overwrites

Individual settings the learner has personally changed are preserved, and they are **told which**:

> *"We changed 6 things. We kept your text size and your button size, because you set those
> yourself."*

Silently discarding a learner's own adjustments because they tried a different preset is a small
betrayal, and it teaches them not to explore.

### Controls are radio groups, not toggles

Real `<fieldset>`, real `<legend>`, real radio inputs. A screen reader announces *"Contrast, High
contrast, radio button, 2 of 2"* — the whole question and the whole answer in one utterance. No
ARIA pattern reproduces that as reliably, and arrow-key navigation within the group comes free.

The input is visually hidden and its sibling is the visible target, because a 44px radio dot is
not a 44px target and the label must be part of the target for a learner with a motor impairment.

### Every change is announced

*"High contrast on."* — so a learner who cannot see the change knows it happened.

### A preview, not a description

Where possible the setting shows its own effect. The text-size control is rendered at each size;
the contrast control shows a sample card in each theme. A learner should not have to imagine what
"Large" means.

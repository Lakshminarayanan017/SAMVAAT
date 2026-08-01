# 03 · Typography

---

## 1. What Duolingo does

### One family, two weights, doing everything

A rounded geometric sans (din-round / Feather). Two weights in practice: **Bold** for anything
structural, **Regular** for prose. There is no light weight, no italic, and almost no
medium — the contrast between "bold" and "regular" is the entire hierarchy.

### Numbers are typographically important

XP, streak count, gem count and the lesson-complete stats are set large and bold, often larger
than the headings around them. The number is the reward, so the number gets the type.

### Sentence case, not title case

Headings read as speech: "Lesson complete!", "You're on a 5 day streak!". Buttons are the
exception — those are **uppercase with letter-spacing**, which makes them read as objects rather
than sentences.

### Observed scale (approximate)

| Use | Size | Weight |
|---|---|---|
| Screen title | 28–32px | Bold |
| Section header | 20–22px | Bold |
| Question prompt | 20–24px | Bold |
| Answer option | 17–19px | Regular |
| Body | 16px | Regular |
| Caption / meta | 13–14px | Regular |
| Button | 15–17px | Bold, uppercase, +0.8px tracking |
| Stat number | 32–40px | Bold |

Line height sits around 1.3 for headings, 1.5 for body.

---

## 2. Why it works

- **Two weights forces hierarchy to come from size and space**, not from six subtle weights that
  most people cannot distinguish. It is a constraint that produces consistency for free.
- **A rounded face reads as friendly and non-institutional** — important for a product a lot of
  people arrive at feeling they are bad at the subject.
- **Big numbers** are the cheapest possible reward. A count that is physically large feels like
  more than the same count set small.
- **Uppercase tracked buttons** are instantly identifiable as controls even in peripheral vision.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| 13–14px captions | Below the Easy-Read floor and hard for low vision. Captions are frequently the text that *explains* something, so this is the worst place to shrink |
| 16px body | Below the 18px Easy-Read minimum |
| Uppercase button text | Measurably slower to read for dyslexic users; screen readers may spell out short uppercase strings; loses word-shape cues |
| Tight 1.3 line height on headings | WCAG 1.4.12 text spacing requires 1.5 to survive user overrides; anything set tighter breaks when a learner applies their own stylesheet |
| Type does not respond to a reading-level setting | An Easy-Read learner gets the same 16px as everyone else |

---

## 4. SAMVAAD specification

### Family

System stack, no webfont:

```
system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Sans Devanagari",
"Noto Sans Tamil", sans-serif
```

Reasons: zero bytes on a metered connection; renders Devanagari and Tamil correctly without a
second download; respects the learner's own OS font size and any dyslexia-friendly face they
have configured system-wide. A custom rounded webfont would look more branded and would cost the
learner data and override their settings — both wrong trade-offs here.

### Base size is 18px, not 16px

Easy-Read requires ≥18px and there is no reason to make everyone else squint so that a default
matches convention. Expressed in `rem` so browser zoom and OS text size still scale it.

### Scale

| Token | Standard | Easy-Read | Line height | Weight |
|---|---|---|---|---|
| `display` | 2.25rem | 2rem | 1.35 | 700 |
| `title` | 1.75rem | 1.625rem | 1.35 | 700 |
| `heading` | 1.375rem | 1.375rem | 1.5 | 600 |
| `body` | 1.125rem | 1.25rem | 1.6 | 400 |
| `caption` | 1rem | 1.125rem | 1.6 | 400 |
| `stat` | 2.75rem | 2.5rem | 1.1 | 700 |
| `button` | 1.125rem | 1.25rem | 1.2 | 600 |

Two deliberate departures from the source:

**Captions grow under Easy-Read; they never shrink.** Small supporting text is exactly what an
Easy-Read reader most needs kept legible, and "captions are small" is a convention rather than a
requirement.

**The Easy-Read scale is compressed, not merely enlarged.** A fluent reader uses a big
display-to-caption spread to skim. An Easy-Read reader is not skimming, and a 2.25rem display
next to 1rem captions is two different reading experiences on one screen.

### Buttons are sentence case

No uppercase, no letter-spacing. Buttons are identified by their fill, size and position — all
of which are stronger signals than case, and none of which costs a dyslexic reader anything.

### Heading level is independent of type size

`<Text variant="caption" as="h2">` is legal and necessary. Document structure is a semantic
decision; type size is a visual one. A section needing smaller type must never cause a skip from
h2 to h4.

### Measure

Prose is capped at **66 characters** standard, **52** under Easy-Read. Beyond that, line-tracking
errors rise measurably — and disproportionately for dyslexic readers.

### Numbers

Stats use `font-variant-numeric: tabular-nums` so a counting-up animation does not shift width
frame to frame. A number that jitters while it counts is a number that is hard to read *and*
looks broken.

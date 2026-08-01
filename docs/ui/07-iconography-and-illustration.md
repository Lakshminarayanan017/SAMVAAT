# 07 · Iconography and illustration

---

## 1. What Duolingo does

### Icons are chunky, filled, and few

A small set — flame, gem, heart, dumbbell, shield, trophy, person — drawn as solid filled shapes
with thick forms and no hairlines. They read at 20px and still read at 20px on a bad screen.

### Icons are used *with* numbers, not alone

The header counters are always icon + number. The icon is the category; the number is the value.
Neither appears without the other.

### Illustration carries the emotional load

Characters appear beside the path, at section boundaries, in empty states and in the celebration.
They are what makes the product feel like a place rather than a form. They are also the single
largest asset cost in the product.

### The mascot is expressive and everywhere

One character with a large library of poses and expressions — celebrating, thinking, sad,
encouraging. It reacts to what the learner does.

---

## 2. Why it works

- **Filled chunky icons survive** small sizes, cheap displays and low vision far better than
  outline icons with 1.5px strokes.
- **Icon + number** is redundant encoding that happens to be accessible: the icon means nothing
  alone, the number means nothing alone, together they are unambiguous.
- **Illustration at section boundaries** breaks a long scroll into places, which is what makes a
  200-lesson course navigable from memory.
- **An expressive mascot** gives the product a relationship. Learners forgive a friend more than
  they forgive a tool.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Header icons unlabelled | A screen reader announces "5" three times with no idea what is being counted |
| A "sad" mascot state on failure | A character that looks let down turns a bad day into a small shaming. For a learner already told they are behind, this is the worst possible moment to add disappointment |
| Mascot animation loops | Permanent motion beside content someone is trying to read |
| Illustration is raster | Does not theme, does not adapt to high contrast, and costs bandwidth on a metered connection |
| Decorative art not hidden from assistive tech | Adds noise to every screen read |

---

## 4. SAMVAAD specification

### Icons

**24px grid, 2px stroke, rounded caps, single path where possible.** Inline SVG with
`fill: currentColor`, so an icon takes the colour of its context and themes automatically.

**Decorative by default.** An icon beside a text label is decoration and is `aria-hidden`.
Announcing both produces "star star, two stars". An icon carrying meaning alone gets a label —
and usually should have been text instead.

**Never focusable.** `focusable="false"` on every SVG; some engines put SVGs in the tab order and
strand a keyboard user on a decoration.

Set required for v2:

```
navigation   home · map · practice · stories · person · settings · trainer · institution
progression  star-filled · star-empty · check · lock-open · flag · sparkle
state        arrow-forward · info · alert · offline · cloud-sync
media        play · pause · replay · mic · keyboard · symbols · hand (ISL) · switch
actions      close · back · plus · minus · hint · download · trash
```

Anything not in that list is a request to add one deliberately, not an excuse to inline an
arbitrary path.

### Illustration is a constrained SVG system

Not commissioned raster art. Eight workplace characters built from a **shared skeleton** with
swappable layers:

```
character = body-shape + skin-tone + hair + clothing + expression + pose
```

Reasons this is the right call here and not merely the cheap one:

- **It themes.** Colours are tokens, so characters work in dark mode and high contrast.
- **Each additional expression costs nothing.** The branching-story system needs
  `{character, expression, intensity}` per branch — dozens of combinations. Raster art would make
  that prohibitive.
- **It scales crisply** at 400% zoom.
- **An engineer can extend it** once a designer defines the parts, so illustration stops being
  on the critical path.

**Representation is not a variant.** The character set includes wheelchairs, hearing aids,
cochlear implants, white canes, AAC devices and prosthetics as **ordinary parts of the shared
skeleton** — not a "diversity" add-on, not a separate category. A learner should see themselves
in the workplace scenes without having gone looking.

### The mascot: Mitra

A common mynah — chosen over the alternatives for reasons recorded in the blueprint. Familiar
across urban India without being sacred, famous for *learning* to speak rather than mimicking
(which matters enormously for a product whose users are accused of "just repeating"), and with a
distinctive silhouette at 24px.

**Five states, and there is no sixth:**

`calm` · `delighted` · `listening` · `thinking` · `greeting`

**There is no sad, disappointed, worried or crying state, and there never will be.** This is a
hard constraint. A mascot that looks let down converts a wrong answer into a small shaming.

**Accessibility contract:**

- `aria-hidden` by default — Mitra is decoration; the message is in the text beside the bird
- Never the sole carrier of any information
- Every animation plays **once**. No idle loop
- Absent during missions entirely
- Respects reduced motion completely

**Personality**: a colleague who has been there a bit longer. Not a teacher, not a coach, not a
therapist. A colleague tells you where the good chai is; a colleague does not congratulate you
for showing up.

| Mitra does | Mitra never |
|---|---|
| Notice specific things | Praise effort alone |
| Share a tip like a peer | Instruct like a teacher |
| Be pleased | Be proud *of* you |
| Wait | Hurry you |

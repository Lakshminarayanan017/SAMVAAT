# 05 · Shape, elevation and the tactile button

---

## 1. What Duolingo does

### Everything is rounded, generously

Buttons ~12–16px radius. Cards ~16px. Progress bars fully rounded. Avatars and node circles are
perfect circles. There is essentially no square corner in the product.

### The signature: a button with an underside

This is the single most recognisable detail in the interface, and it is four lines of CSS.

```
face:      the button, filled with the brand colour
underside: the same colour, ~20% darker, revealed as a 4px band beneath
press:     face translates down 4px; the band collapses to 0
```

The result reads as a physical key being pressed. Combined with a ~90ms transition it produces
a genuinely satisfying tactile response with no images, no shadows and no JavaScript.

### Cards have a hairline border, not a shadow

Most surfaces are separated by a 2px light border rather than a drop shadow. Shadows appear only
on genuinely floating things — sheets, the feedback banner, popovers.

### Selection is a fill *and* a border change

A selected answer card gets a light blue wash plus a 2px blue border. Two signals for one state.

---

## 2. Why it works

- **Consistent generous radius** is most of what makes the product read as "friendly" rather
  than "enterprise". It is one token doing enormous brand work.
- **The underside** gives physicality without skeuomorphism, costs nothing to render, and works
  in every theme because it is derived from the fill colour rather than being a fixed shadow.
- **Borders over shadows** survive on cheap displays where subtle shadows disappear entirely.
- **Two signals for selection** is accidentally good accessibility — they did it for visual
  punch, but it happens to be the correct pattern.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Elevation in the sheet/modal layer is shadow-only | Shadow vanishes completely in forced-colours mode and on high-contrast themes. Every card boundary on screen disappears at once |
| The press animation is not suppressed under reduced motion | A 4px translate is small, but it is still motion the learner asked not to have |
| Disabled buttons are grey with no other signal | Colour-only state |
| Some pressable cards are `<div>` with a click handler | Not focusable, not Enter/Space activatable, invisible to switch scanning |

---

## 4. SAMVAAD specification

### Radius

| Token | Value | Use |
|---|---|---|
| `--r-1` | 8px | Chips, small controls |
| `--r-2` | 14px | Buttons, inputs |
| `--r-3` | 20px | Cards, sheets |
| `--r-4` | 28px | Hero surfaces, the celebration card |
| `--r-full` | 999px | Pills, avatars, node circles, progress tracks |

### Elevation — always border *and* shadow

Four levels. Shadow is reinforcement; **border weight carries the information**, because shadow
is not rendered at all in forced-colours mode or on the high-contrast themes.

| Level | Border | Shadow | Use |
|---|---|---|---|
| `flat` | 1px | none | Inline groupings |
| `raised` | 1px | `0 1px 2px rgb(0 0 0 / .06)` | Cards |
| `lifted` | 2px | `0 6px 16px rgb(0 0 0 / .10)` | The active thing on a screen |
| `over` | 2px | `0 14px 40px rgb(0 0 0 / .18)` | Sheets, dialogs, the feedback banner |

A test asserts no level has a zero border.

### The tactile button

Kept, because it is genuinely excellent, and made safe:

```
--lift: 4px

face      background: var(--brand)
underside box-shadow: 0 var(--lift) 0 0 var(--brand-press)
hover     background: var(--brand-hover)
active    transform: translateY(var(--lift))
          box-shadow: 0 0 0 0 var(--brand-press)
```

Rules:

1. **Under reduced motion the transform is dropped and the underside collapses instantly.**
   The press still reads as a press; it simply does not travel.
2. **In forced-colours mode the underside is replaced by a 2px border.** `box-shadow` is not
   rendered there, so without this the button would lose its only depth cue.
3. **The layout reserves `--lift`** in the button's box, so pressing never shifts the elements
   below it. A page that jumps 4px on every tap is a page that feels broken.
4. **Disabled is not grey-only.** It is reduced opacity, `cursor: not-allowed`, `aria-disabled`,
   *and* the underside removed — so the control visibly stops looking pressable.

### Pressable cards are buttons

Any card with an `onClick` renders a real `<button>`. A `<div>` with a click handler is not
focusable, not activatable by Enter or Space, and invisible to switch scanning — and a clickable
card is the single most common place this gets forgotten.

Interactive cards require an explicit `label`, because otherwise the accessible name is the
concatenation of everything inside: *"World 4 Speaking Up For Yourself 3 of 5 levels 2 stars"*,
with no indication of what pressing it does.

### Selection state

Three signals, always: **fill change + border weight change + a check glyph**. Never fill alone.

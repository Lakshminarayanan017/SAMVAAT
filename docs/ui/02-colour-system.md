# 02 · Colour system

---

## 1. What Duolingo does

### One dominant brand colour, used as *the* affordance

A single saturated green is the primary action colour, and it is used almost nowhere else. If
something is that green, it is pressable and it is the main thing on the screen. That consistency
is doing more work than the specific hue.

### Every button has an "underside"

The primary button is a lighter face over a darker version of the same hue, offset by 4px
downward. Pressing translates the face down and collapses the offset. The whole tactile quality
of the interface comes from this one trick.

### Unit colours

Each unit of the course has its own hue. The section header, the path nodes and the lesson chrome
all take it. Scrolling through the course is visibly moving through coloured regions, which gives
a long course a sense of place.

### Semantic colours are loud

- Correct: bright green fill, dark green text
- Incorrect: pink/red fill, dark red text
- Locked: flat grey
- Currency: gold, blue, red for the three counters

### Approximate values observed

| Role | Approx | Notes |
|---|---|---|
| Primary | `#58CC02` | Underside `#58A700` |
| Correct fill | `#D7FFB8` | Ink `#58A700` |
| Incorrect fill | `#FFDFE0` | Ink `#EA2B2B` |
| Locked | `#E5E5E5` | Ink `#AFAFAF` |
| Body ink | `#4B4B4B` | On white |

---

## 2. Why it works

- **Scarcity of the brand colour** makes it mean "press this". A palette where five things are
  green teaches nothing.
- **The underside** costs one extra colour per button and buys a physical, satisfying press. It
  is the single highest return-on-effort detail in the whole interface.
- **Unit colours** give a 200-lesson course spatial memory: "the blue section" is a real thing a
  learner remembers.
- **Loud semantics** mean the learner never has to read to know whether they got it right; the
  peripheral colour tells them before their eyes reach the text.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| `#4B4B4B` body ink on white is **7.5:1** — fine — but their *secondary* greys drop to ~3:1 | Fails AAA and often AA. A low-vision learner cannot read the supporting text |
| Correct/incorrect distinguished primarily by red vs green | The single most common colour vision deficiency is red-green. This is the worst possible pairing for a right/wrong signal |
| Locked grey carries meaning with no text | A learner who cannot perceive the grey has no idea the content is unavailable |
| Red for a wrong answer | Red is an alarm colour. For a learner with communication anxiety, an alarm on a practice attempt is exactly wrong |
| Saturated green fill at large area | Visual stress trigger for some migraine and photosensitivity profiles |

---

## 4. SAMVAAD specification

### Identity

Warm, not clinical. Paper rather than screen. The existing product reads as a well-built form;
v2 should read as something made for a person.

**Primary is jade** — growth and calm, distinct from the medical/corporate blues and the
"education app" greens, and legible against a warm ground.

### Light theme (verified)

| Token | Value | Role |
|---|---|---|
| `--canvas` | `#FBF8F4` | The page. Warm paper |
| `--surface` | `#FFFFFF` | Cards, raised |
| `--sunken` | `#F6F1EA` | Wells, tracks, disabled |
| `--ink` | `#1C1917` | Body text |
| `--ink-soft` | `#4B4642` | Secondary text — **held to the same 7:1 bar** |
| `--brand` | `#0A5A50` | The one pressable colour |
| `--brand-press` | `#063A34` | Button underside |
| `--on-brand` | `#FFFFFF` | Text on brand |
| `--good-ink` | `#0B5730` | Success text |
| `--good-wash` | `#E7F5EC` | Success fill |
| `--try-ink` | `#6E3C00` | "Not quite yet" text — **amber, never red** |
| `--try-wash` | `#FBF0E2` | "Not quite yet" fill |
| `--info-ink` | `#1C4E80` | Neutral emphasis |
| `--line` | `#D9D2C8` | Hairlines |
| `--line-strong` | `#57534E` | Control outlines |
| `--focus` | `#B45309` | Focus ring — deliberately *not* the brand hue |

### Dark theme

| Token | Value |
|---|---|
| `--canvas` | `#14100E` |
| `--surface` | `#1E1916` |
| `--sunken` | `#0D0A09` |
| `--ink` | `#F7F3EE` |
| `--ink-soft` | `#C4BCB4` |
| `--brand` | `#5EE0C8` |
| `--brand-press` | `#3FBFA8` |
| `--on-brand` | `#0A1512` |
| `--good-ink` | `#6FE39B` |
| `--try-ink` | `#F5C168` |
| `--focus` | `#FFD166` |

### High contrast (both schemes)

Pure black/white, `--ink-soft` collapses to `--ink`, all fills become the canvas colour and
**separation is carried entirely by borders**. Success and attention inks collapse to the
foreground ink — colour is unavailable, so text carries everything.

### Rules

1. **The brand colour means "press this" and nothing else.** It is never a decoration, never a
   heading colour, never a background wash. One pressable colour, everywhere.
2. **World colours are for world identity only.** A world hue never appears on a control. A
   learner must never have to work out whether a colour is telling them *where they are* or
   *what to press*.
3. **Correct vs not-yet is never green vs red.** It is jade-green + a check + the word, against
   amber + an arrow + the words "Not quite yet". Different hue, different icon, different text,
   and the amber is a *lower*-arousal colour than red on purpose.
4. **Every ink meets 7:1 on every surface it can land on**, including `--ink-soft`. "Muted" is a
   visual weight, not a licence to fail.
5. **The focus ring is not the brand hue.** It has to be visible *on* a brand-filled button, so
   it is a different family entirely, and it is drawn two-tone (surface-coloured inner ring +
   focus outer ring) so it works on any fill.

### World palette

Ten hues, one per world, each verified at 7:1 against both canvas colours, and each chosen to
differ in **lightness** as well as hue so they remain distinguishable in greyscale.

Every world also carries an **icon silhouette** and its **number and name in text**, so the
colour is the third of three signals, never the first.

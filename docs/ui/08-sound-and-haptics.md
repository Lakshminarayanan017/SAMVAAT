# 08 · Sound and haptics

---

## 1. What Duolingo does

### A small, consistent sound vocabulary

| Event | Sound |
|---|---|
| Correct answer | Bright rising two-note chime |
| Wrong answer | Short low buzz |
| Lesson complete | Short fanfare |
| XP tick | Rapid soft clicks under the counting number |
| Streak extended | Warm ascending flourish |
| Button press | Soft click |

All short — most under 400ms.

### Haptics accompany the important ones

A light tap on correct, a heavier double on incorrect, a pattern on completion. On mobile, the
haptic often lands before the sound is processed, so it is doing more work than it appears to.

### Sound is on by default, with a toggle in settings

### Audio for content is separate from audio for feedback

The word/sentence audio (a speaker button on the prompt) is a different system from the
interface sounds, with its own controls including a slow-playback option.

---

## 2. Why it works

- **A two-note rise for correct and a low buzz for wrong** is a second channel carrying the same
  information as the colour and the text. Redundant encoding, done for feel, accidentally good
  accessibility.
- **Haptics arrive faster than vision**, so the answer feels acknowledged instantly.
- **Ticking under a counting number** is what makes the count feel like accumulation rather than
  animation.
- **A short vocabulary** — six sounds — becomes learned within a session and then stops being
  noticed while still carrying meaning.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Sound on by default | A learner practising in a shared room, a classroom or on a bus is announced to everyone around them. For someone self-conscious about being seen using a disability aid, this is a reason to close the app |
| A distinct "wrong" buzz | An audible failure signal in a public place. Worse than the visual one, because other people hear it |
| Haptics not separately controllable | Some learners want haptics *instead of* sound, not as well |
| Sound treated as decoration | It is not. For a blind learner it may be the primary feedback channel, so it must be complete rather than ornamental |

---

## 4. SAMVAAD specification

### Sound is **off by default**, and this is deliberate

Duolingo can default sound on because being overheard practising Spanish carries no cost. Being
overheard practising *"Could you repeat that, please?"* on a communication-skills app, in a
classroom or a shared home, is a different thing entirely.

Turning it on is one action in settings, and the first-run confirmation offers it explicitly, so
a blind learner who wants audio feedback is not left hunting.

### Three independent switches

| Setting | Default | Notes |
|---|---|---|
| Interface sounds | **off** | Feedback and celebration |
| Haptics | **on** | Silent, private, and useful. Ignored where unsupported |
| Content audio | **on** | Narration of phrases. A different system — see below |

Independent because the needs genuinely diverge: a Deaf learner wants haptics and no sound; a
blind learner wants sound and content audio; a learner on a bus wants haptics only.

### The vocabulary

| Event | Sound | Haptic |
|---|---|---|
| Answer accepted | Two-note rise, ≤300ms | Light single |
| Not quite yet | **Neutral single tone, not a buzz** | Light double |
| Level complete | Short warm flourish, ≤700ms | Light triple |
| XP counting | Soft ticks under the number | none |
| Star landing | One soft tone per star | none |

**There is no failure buzz.** A low descending "wrong" tone is an audible verdict, and the copy
rule everywhere else in this product is that a wrong answer produces coaching, not a verdict.
The sound follows the copy: a neutral tone that means *"noted, keep going"*, not *"no"*.

### Content audio is a separate system

The phrase narration has its own controls and always includes:

- **Replay, unlimited and prominent.** Never a limited number of listens
- **Slow playback**, using the recorded slow track where one exists rather than time-stretching
- **A visible transcript** at all times — captions are not optional and never a toggle

### Implementation

- Web Audio for interface sounds, preloaded once, ≤8KB total. No sound is ever the reason a
  screen is slow
- `navigator.vibrate` for haptics, feature-detected, silently absent where unsupported
- Every sound has a text equivalent already on screen. **No sound is ever the only signal** — if
  the audio fails to load, nothing is lost

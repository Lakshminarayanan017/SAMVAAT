# The Five Personas

Every feature in SAMVAAD is tested against these five learners. A feature that fails any one of
them is not shippable — this is [Ethics rule E7](ETHICS_CHARTER.md#e7--a-feature-that-fails-any-persona-is-not-shippable).

They are not marketing personas. They are **test fixtures**. The persona walkthrough suite in
`apps/web/tests/personas/` runs each of them through the full product every sprint.

---

## P1 · Ravi — 24, warehouse operations applicant

| | |
|---|---|
| **Disability** | Low vision (approximately 10% residual vision) |
| **Input channels** | Voice, keyboard |
| **Output channels** | Audio, screen reader, high contrast, haptics |
| **Assistive tech** | TalkBack on Android, NVDA on desktop, 400% zoom |
| **Goal** | Pass a warehouse operations interview |

**What breaks him:** information conveyed only by colour, position, or an unlabelled icon.
Charts without a data-table equivalent. Focus that jumps unpredictably. Toast notifications that
vanish before a screen reader announces them.

**His acceptance test:** completes onboarding, a drill, a role-play, and a mock interview
**with the monitor switched off**.

---

## P2 · Meena — 22, data-entry applicant

| | |
|---|---|
| **Disability** | Profoundly Deaf; Indian Sign Language is her first language |
| **Input channels** | Typing, sign (camera) |
| **Output channels** | Captions, ISL clips, visual cues, haptics |
| **Assistive tech** | None beyond the app; ISL fluent, written English is her second language |
| **Goal** | Handle a workplace where everyone else speaks |

**What breaks her:** audio-only instructions. Captions that lag or paraphrase. English idiom
and long sentences — written English is not her native language, so text-heavy is not
automatically accessible to her. An ISL avatar with wrong grammar is worse than no avatar.

**Her acceptance test:** completes a full scenario using **sign input and ISL output only**,
never hearing a sound.

---

## P3 · Arjun — 27, packaging unit trainee

| | |
|---|---|
| **Disability** | Cerebral palsy — dysarthric speech, limited fine motor control |
| **Input channels** | Voice (atypical), switch / scanning, large targets |
| **Output channels** | Audio, captions |
| **Assistive tech** | Two-switch scanning interface |
| **Goal** | Ask his supervisor for help without being misunderstood |

**What breaks him:** standard ASR failing him completely — base Whisper word error rate on
dysarthric speech can exceed 50%. Small tap targets. Any time limit. Drag interactions.
Interfaces that assume a mouse or precise touch.

**His acceptance test:** completes a drill using **two-switch scanning only**, and his
personalised ASR shows a measurable word-error-rate improvement over the base model.

---

## P4 · Fatima — 20, retail floor trainee

| | |
|---|---|
| **Disability** | Intellectual disability (mild) |
| **Input channels** | Symbol tap (AAC), simple voice |
| **Output channels** | Easy-Read, pictographs, slow narrated audio |
| **Assistive tech** | AAC symbol board (ARASAAC) |
| **Goal** | Learn what to say on her first day |

**What breaks her:** dense text. Multi-step screens. Abstract instructions. Anything framed as
failure. Vocabulary above roughly a Grade-4 reading level. More than one idea per screen.

**Her acceptance test:** completes a role-play by **composing answers from picture symbols**,
with one exercise per screen and no wall of text at any point.

---

## P5 · Karthik — 25, IT support applicant

| | |
|---|---|
| **Disability** | Stammer (moderate to severe), with associated anxiety |
| **Input channels** | Voice, typing |
| **Output channels** | Audio, captions |
| **Assistive tech** | None |
| **Goal** | Get through an interview without being scored on how he speaks |

**What breaks him:** being timed. Being scored on fluency. The AI interrupting him during a
block. Feedback that lists his disfluencies as errors. A progress chart that goes down on a bad
speech day.

**His acceptance test:** completes a mock interview where the **disfluency-invariance test**
holds — his score is provably unaffected by his stammer — and every detected block produces a
coaching cue, never a deduction.

---

## The design rules these five produced

Each of these is a direct consequence of a persona, not a general principle we liked.

| Rule | Comes from |
|---|---|
| **Never use time pressure as a difficulty mechanic** | P3, P4, P5 — it excludes three of five in one decision |
| **Every chart needs a data-table equivalent and a text summary** | P1 |
| **Text is not automatically accessible** | P2 — written English is her second language |
| **One idea per screen for Easy-Read profiles** | P4 |
| **Disfluency produces coaching cues, never deductions** | P5 |
| **Every activity has a non-speech path** | P3 when ASR fails, P2 always |
| **Minimum 44×44px targets, configurable to 88px** | P3 |
| **Recording has no maximum duration** | P3, P5 |

---

## Using these in a pull request

Every PR states which personas it was tested against:

```
Tested against: P1 (screen reader, monitor off), P4 (AAC input, Easy-Read)
Not applicable: P2 (no sign surface touched)
```

"All five" is only a valid answer if you actually ran all five.

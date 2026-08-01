# 14 · Exercise types

---

## 1. What Duolingo does

| Type | Interaction |
|---|---|
| **Select the image** | 3–4 image+word tiles, tap one |
| **Translate to X** | Tap word tiles from a bank to build a sentence |
| **Translate (free)** | Type into a text field |
| **Listen and type** | Audio plays, learner types what they heard |
| **Speak** | Microphone, ASR scores the utterance |
| **Match pairs** | Two columns, tap to pair them |
| **Fill the blank** | Sentence with a gap, choose or type |
| **Complete the chat** | A conversation with the learner's turn missing |
| **Sort into order** | Drag/tap tiles into sequence |

Perhaps twelve types in total, mixed within a lesson so no two consecutive questions feel the
same.

### Common structure across all of them

Every type has the same anatomy: **prompt at the top, interaction in the middle, CHECK at the
bottom, feedback banner from below**. Only the middle changes.

### Skip options

Speak and Listen exercises have "Can't speak now" / "Can't listen now", which suppress that type
for an hour.

---

## 2. Why it works

- **Constant anatomy, varying middle** means a new exercise type is learnable instantly — the
  learner only has to parse the new part.
- **Mixing types** prevents the pattern-matching that makes drilling feel mechanical.
- **The word bank** lets a beginner produce a sentence they could not have typed, which is a real
  scaffolding insight.
- **Per-type skips** acknowledge context (you are on a bus) without penalty.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Drag-to-order | Motor impairment, switch access and screen readers all handle drag badly. Usually there is no non-drag alternative |
| Speak scored by ASR | ASR trained on typical speech systematically mis-scores atypical speech. Scoring it means scoring the disability |
| "Can't speak now" suppresses for **an hour** | Framed as temporary. For a non-speaking learner it is permanent, and they have to re-decline every hour, forever |
| Match-pairs needs two columns | Breaks at 400% zoom |
| Listen exercises with no transcript | Unusable for a Deaf learner; the skip removes the exercise rather than making it accessible |
| Image-select relies on recognisable illustration | Unusable at low vision without alt text, which is often absent |

The pattern: **accessibility is handled by letting the learner opt out of an exercise type**,
which quietly gives them a smaller course than everyone else.

---

## 4. SAMVAAD specification

### The principle: a situation with a constraint

The difference between a quiz and a puzzle:

> "Which of these means 'please repeat'?" — a quiz question
> "Your supervisor said three things and the machine was loud. You caught the first. What do you say?" — a puzzle

Same phrase, same recall, entirely different experience. **Every mission type is framed as a
situation with a constraint.**

### Eight types

| Type | The verb | The constraint that makes it a puzzle | Built |
|---|---|---|---|
| `recognise` | Connect meaning to phrase | Distractors are *plausible*, drawn from the same chapter | ✅ |
| `choose_in_context` | Pick what the room expects | All options are grammatically correct; only one fits the relationship | ✅ |
| `produce` | Say it your way | Any channel. Never "say it correctly" — "say it so it lands" | ✅ |
| `order_the_steps` | Sequence an exchange | The pieces are a real conversation, out of order | planned |
| `scenario` | Choose a response, see consequence | The world reacts and the story continues | planned |
| `roleplay` | Multi-turn conversation | An AI colleague, grounded in the world's phrases | planned |
| `read_the_room` | Read an authored character | Comprehension of *their* expression — never measurement of the learner's | planned |
| `catch_it` | Identify what was asked | Noise or ambiguity. **Never** time; replay is unlimited | planned |

A level declaring an unbuilt type **falls back** rather than being empty. A learner must never
meet a blank level because a feature is unfinished.

### Five properties every mission type must satisfy

Checked by a shared harness that runs **each type × each input adapter**. A ninth type added
without these fails there rather than in a learner's session.

1. **Answerable in every input channel the learner's profile offers.** A mission with one answer
   path excludes a persona.
2. **No time limit anywhere.** Not a countdown, not a bonus, not a "you took a while".
3. **Unlimited retries at no cost.** No hearts, no lives, no progress lost.
4. **A scaffold available at all times** — hint, sentence starter, or narrowed choices. Requesting
   one lowers the FSRS grade and **never** lowers XP.
5. **A wrong answer produces coaching, never a verdict.**

### No drag, anywhere

`order_the_steps` is built as **tap-to-place**: tap a piece, tap its slot. Or move a selected
piece with the arrow keys. Equivalent expressiveness, and it works with switch scanning, a screen
reader and a tremor.

Drag-and-drop with "an accessible alternative" is two implementations, and the alternative is
always the one that rots.

### `produce` is self-assessed, not ASR-scored

The learner says or types the phrase, then reports: **"I said it"** / **"I need more practice"**.

Speech analysis still runs when the learner has consented — for their **own** feedback on the
progress screen — but it never decides whether the mission was passed. Putting ASR quality
between a learner and their own progress is the exact failure mode this product exists to avoid.

### There is no per-type skip

Because there is nothing to skip. The mission arrives in the learner's channel via the modality
router: a non-speaking learner does not "skip the speaking exercise", they get the same mission
as an AAC composition.

**This is the single biggest structural difference from Duolingo in this file.** They make
exercises accessible by letting you decline them, which yields a smaller course. We make the
*content* modality-neutral and choose the rendering at runtime, so everybody gets the whole
course.

### Distractors come from the same chapter

A distractor from a different world is obviously wrong and teaches nothing. One from the same
chapter is a phrase the learner is also learning, so choosing between them is the actual skill.

Answer position is shuffled per learner and stable per level, so reopening never reshuffles —
but the answer is never always in the same slot, which is a pattern a learner finds before they
find the phrase.

# 26 · Onboarding

The first 90 seconds. The highest-stakes screens in the product.

---

## 1. What Duolingo does

### The sequence

```
1  Splash → "Get started" / "I already have an account"
2  "How did you hear about us?"
3  Choose a language
4  "Why are you learning?"
5  "How much time per day?"      (5 / 10 / 15 / 20 min)
6  "How much do you know?"       (from scratch / placement test)
7  → straight into a lesson
8  after the lesson: "Create a profile to save your progress"
```

### The critical structural decision

**The learner completes a lesson before being asked to sign up.** No account, no email, no
password until after the first success.

### Each question is one screen

Large tappable cards, one question, a single Continue. No forms, no keyboard until step 8.

### Progress is shown as a bar across the top

The learner can see the onboarding is finite.

---

## 2. Why it works

- **Deferring signup past the first success** is the single highest-leverage decision in the whole
  product. Commitment is asked for after value has been demonstrated, not before.
- **One question per screen** keeps the perceived effort near zero even across seven screens.
- **Card answers, not text fields** means no keyboard, which is the main source of mobile
  onboarding drop-off.
- **The "why are you learning" question** does almost nothing functionally, but it makes the
  learner state an intention out loud, which measurably increases follow-through.
- **A visible onboarding progress bar** stops it feeling open-ended.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Onboarding assumes the learner can read the first screen | Everything from step 1 is text. A learner who needs symbols, audio or ISL cannot get through the screen that would have told us that |
| Marketing questions before value | "How did you hear about us?" spends the learner's patience on our analytics |
| Time commitment framed as ambition | "Intense — 20 min/day" frames a shorter session as less serious, when for our learners it is often a medical constraint |
| No accessibility questions at all | The most important thing about our learner is asked nowhere |
| Placement test | A test as the second interaction, for a population routinely assessed and found wanting |

---

## 4. SAMVAAD specification

### The order is inverted: accessibility first, everything else later

The single most important fact about our learner is *how they need to be spoken to*, and it must
be established **before the first sentence they are asked to read**.

### The sequence

```
0  ZERO INPUT      read OS preferences, apply before first paint
1  FOUR DOORS      how would you like to be spoken to?
2  FIRST WIN       one mission. no account. ~60 seconds in
3  THE MAP         "that is where this goes"
4  PROFILE         (optional) "does one of these sound like you?"
5  CONFIRM         pace, captions, session length — in their channel
6  KEEP IT         (optional, later) save your progress
```

**Constraint: the first mission is reachable within 90 seconds**, including all of the above.
Onboarding that outlasts the first win loses the learner before the product has shown them
anything.

### Stage 0 — zero input

Before anything renders, read `prefers-reduced-motion`, `prefers-contrast`,
`prefers-color-scheme`, pointer type and viewport. Apply immediately.

A learner who has already configured their OS should find the app **already correct** when it
opens. Asking them to re-state preferences the browser already told us is asking them to do work
we did not need them to do.

### Stage 1 — the four-door screen

**The hardest UI in the product.** Four huge targets, each simultaneously labelled in **text,
pictograph, audio and ISL** — so whichever channel the learner has, the screen is readable.

```
┌──────────────────┬──────────────────┐
│   [symbol]       │   [symbol]       │
│                  │                  │
│   I can read     │   Read it to me  │
│   this fine      │                  │
├──────────────────┼──────────────────┤
│   [symbol]       │   [symbol]       │
│                  │                  │
│   Show me        │   I use sign     │
│   pictures       │   language       │
└──────────────────┴──────────────────┘
```

- Each door ≥ 160px tall, full half-width
- Reachable by tap, keyboard, switch scan and voice control
- Audio auto-narrates each door on focus
- **No Continue button** — choosing a door *is* continuing. One action, not two

Everything after this screen renders in the chosen channel.

### Stage 2 — the first win, before any account

One mission. The learner gets it right — the first mission is deliberately winnable — Mitra
reacts, a star lands, XP counts.

**No account, no email, no password, no form.** A guest session already exists; identity is
deferred entirely.

The emotional beat is *"I did that"*, and it must happen before any friction.

### Stage 3 — the map

They see ten worlds. They see the last one is **The Interview**. They see **it is not locked**.

*"That is where this goes, and it is for me."*

### Stage 4 — the learning profile, optional

> **"Does one of these sound like you?"**

Sixteen cards, plain language, Easy-Read label, and **what choosing it changes stated before
committing**.

Three rules that make this safe:

1. **"I would rather not say" is the first option, and it is a complete answer.** It must not
   produce a worse experience — it configures the widest-compatibility preset
2. **It is never stored as a diagnosis.** `learning_profile_id` is a preset, nullable, and
   overridable setting-by-setting
3. **Skippable.** A learner who does not want to answer reaches the same product

### Stage 5 — confirmation, in the chosen channel

Pace, captions, session length — asked **through** the channel Stage 1 established, so the
confirmation is itself proof the choice worked.

### Stage 6 — keeping progress, offered later and never demanded

Guest sessions persist locally. The upgrade prompt appears after the third session, framed as
*"save this to another device"*, never as a wall.

### What is never asked

- Date of birth. Only *"Are you under 18?"*, once, because it changes guardian consent — a real
  purpose, and DPDP Act data minimisation requires one
- Diagnosis
- "How did you hear about us"
- Any placement test
- Any question whose answer we do not immediately use

### Onboarding must be resumable

A learner interrupted at stage 4 resumes at stage 4. Nothing is lost, and nothing restarts.

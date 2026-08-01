# 17 · Dialogue and AI conversation

Duolingo's newest surface, and the closest thing they have to what SAMVAAD actually teaches.

---

## 1. What Duolingo does

### Video Call / Roleplay

A character appears; a conversation runs turn by turn. The learner types or speaks a reply, and
the model responds in character. There is a scenario framing ("You are ordering coffee") and a
summary at the end.

### The chat exercise

A simpler version: a scripted conversation with the learner's turn missing, chosen from options.

### Structure

```
[ character portrait ]
  their line
                     your line
  their line
                     [ your turn — type or speak ]
```

Right-aligned learner turns, left-aligned character turns. The standard messaging metaphor,
because everybody already knows it.

### The end

A summary card: what went well, one thing to work on, XP.

---

## 2. Why it works

- **The messaging metaphor needs no explanation.** Zero learning cost.
- **A named scenario** turns an abstract exercise into a situation, which is the difference
  between a quiz and a puzzle.
- **Turn-by-turn** keeps working memory load low — one thing at a time, same as everywhere else.
- **The character portrait** makes it a conversation with someone rather than a text field.

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| Voice-first framing | The feature is presented as speaking practice; a non-speaking learner is second-class in it |
| Response speed implicitly matters | A conversation UI creates pressure to reply quickly. AAC composition takes minutes |
| No composition scaffold | No sentence starters, no phrase bank shortcut |
| Model tone is not disability-aware | Generic LLM warmth reads as condescending to an adult with an intellectual disability |
| No exit mid-conversation | Leaving a conversation feels like walking out on someone |
| Summary can comment on fluency | Directly scores the disability |

---

## 4. SAMVAAD specification

The existing GenAI service already has the hard parts: a provider interface with a first-class
scripted fallback, versioned hashed prompts, RAG over the phrase bank, and a six-check guardrail
chain **including a condescension filter**. This file is about the surface over it.

### Layout

```
┌──────────────────────────────────────────┐
│ [ Leave ]     Practising: asking for help │
├──────────────────────────────────────────┤
│                                           │
│  [Priya]  Can you help me with this?      │
│                                           │
│                        You said:  ────────│
│                 "Yes, what do you need?"  │
│                                           │
│  [Priya]  I can't reach the top shelf.    │
│                                           │
├──────────────────────────────────────────┤
│  Your turn                                │
│  [ modality input — text / AAC / speech / │
│    switch / sign, per profile ]           │
│                                           │
│  Not sure? [ Show me some ways to start ] │
└──────────────────────────────────────────┘
```

### Every turn is a `ContentBlock`

Both the character's lines and the learner's options go through the modality router. A choice
arrives as text for one learner, three tappable symbols for another, ISL for a third — with no
branching in this component. That is the whole reason a turn carries a `block_id` rather than a
string.

### Nothing is timed, and nothing implies speed

- No typing indicator that suggests the character is waiting
- No "still there?" prompt
- No response-time measurement, anywhere, ever
- The character's reply is not delayed to feel realistic — it arrives when it arrives

A conversation UI creates *implicit* time pressure even with no timer. For a learner composing on
an AAC board at two words a minute, every one of those cues is a reason to stop.

### The composition scaffold is prominent, not hidden

`Show me some ways to start` is always visible, and offers three sentence starters drawn from the
world's phrase bank. Using one is normal practice, not cheating, and it is exactly the
`compose_ahead` / `phrase_bank_shortcut` strategy the non-speaking and aphasia profiles specify.

### Leaving is free

`Leave` exits immediately. The conversation is saved and resumable. No confirmation, no warning,
and the character never reacts to being left.

### The AI's register is composed from profile fragments

```
base_workplace_colleague
  + profile_fragment(non_speaking)   "Never ask the learner to speak or read aloud.
                                      Never comment on speed of reply."
  + strategy_fragment(compose_ahead)
  + register_fragment(easy_read)
```

Each fragment is data, hashed and versioned, so a generation stays interpretable months later.
The condescension filter runs against **every profile × every scenario**, not a sample.

### The summary comments on content, never delivery

> **What worked:** you asked what she needed before offering.
> **One thing to try:** you could say what you *can* do, as well as what you can't.

Never: fluency, pace, hesitation, filler words, response time, tone, or confidence. Those are the
E2 exclusion list, and they are the disability.

### Sensitive scenarios carry an exit and a route to a person

Disclosure and adjustment conversations show, before starting, that the learner can stop at any
time and that nothing is recorded as a failure — plus a way to reach a real human.

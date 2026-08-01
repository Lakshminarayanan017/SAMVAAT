# SAMVAAD Ethics Charter

**Status:** Binding · **Version:** 1.0 · **Adopted:** 2026-07-31

---

## Why this document exists

The most common way a project like SAMVAAD fails is not technical. It is that the team builds
the AI first, ships something that quietly penalises disability, and only discovers it once
every downstream feature already depends on the unfair score.

So we write the constraints down **before** the code, and we make them **testable**. Every rule
below has an enforcing test named next to it. A rule with no test is a wish, not a constraint.

This charter is not aspirational language for a pitch deck. It is a specification.
If a feature conflicts with a rule here, **the feature changes.**

---

## The seven rules

### E1 · No learner is ever compared to a non-disabled reference speaker

No score, label, chart, or message shown to a learner may be derived from a comparison against
a "normal", "native", or "typical" speaker.

All scoring is **baseline-relative**: measured against the learner's own rolling baseline.

> **Why.** A pronunciation scorer that compares a person with dysarthria to a neurotypical
> native speaker will return a low score forever, regardless of effort or improvement. The
> learner correctly concludes the tool is useless and leaves. Comparison to a norm they were
> never going to meet is not assessment; it is discouragement with a number attached.

**Enforced by** · `services/speech/tests/test_ppi.py` — `TestNoReferenceComparison`
**Implemented in** · `services/speech/pipeline/ppi.py` (M7)

---

### E2 · The interview rubric may not grade any manifestation of disability

This is the canonical list. It is read by CI and by `services/genai/rubric/`; changing it
here changes the enforced behaviour, and nowhere else does.

```yaml
# rubric-v1
SCORED DIMENSIONS:      # the rubric may grade exactly these
  - content_relevance
  - structure_star
  - specificity
  - clarity_of_intent
  - self_advocacy
  - role_alignment

EXCLUDED DIMENSIONS:    # the rubric MUST NOT grade any of these
  - speech_rate
  - articulation_quality
  - fluency
  - disfluency
  - accent
  - voice_quality
  - gaze
  - eye_contact
  - facial_affect
  - body_posture
  - motor_stillness
  - response_latency
  - grammatical_perfection
  - vocabulary_sophistication
```

Enforcement is architectural, in four independent layers:

1. **Input scrubbing** — the scorer receives a normalised transcript with disfluencies removed,
   pauses collapsed, and timing stripped. It is structurally blind to the excluded traits.
   *You cannot penalise what you never received.*
2. **Schema constraint** — the response schema has exactly the six scored fields. There is no
   field an excluded trait could occupy.
3. **Invariance test in CI** — see below.
4. **Audit record** — every score persists the rubric version, the scored dimensions, the
   excluded dimensions, the prompt hash, and the model ID.

> **Why.** AI hiring tools have a documented record of filtering out disabled candidates by
> scoring exactly these traits. We are building an interview scorer for disabled people. If we
> reproduce that behaviour we have built the harm we set out to prevent.

**Enforced by** · `services/genai/tests/test_rubric.py` — `TestDisfluencyInvariance`
**Implemented in** · `services/genai/rubric/` (M11)

#### The disfluency-invariance test

The single most important test in this repository.

```
for transcript in fixture_set:
    clean    = score(transcript)
    degraded = score(inject_disfluencies(transcript))   # fillers, blocks,
                                                        # repetitions, long pauses,
                                                        # identical content
    assert abs(clean.total - degraded.total) < EPSILON
```

If injecting disfluency changes the score, **the build fails.** This converts a fairness claim
into a fairness proof.

---

### E3 · Raw audio is deleted within 24 hours of feature extraction

Unless the learner has given separate, explicit, independently revocable consent to contribute
to the research corpus.

Retention is a **column with a TTL and a job that enforces it**, not a sentence in a privacy
policy. Voice is treated as biometric data and held to the highest tier in the data map.

**Enforced by** · `apps/api/tests/test_audio_retention.py`
**Implemented in** · `apps/api/app/security/retention.py` (M5, M17)

---

### E4 · Video never leaves the device

Camera input — for Indian Sign Language recognition, and for the optional posture/gaze cues —
is processed entirely on-device. Only the resulting label or cue leaves the client. No video
frame is transmitted, stored, or logged, at any quality, for any purpose, ever.

**NOT YET ENFORCED** · no camera code exists yet. The test lands with sign
input in M16 and must assert on network traffic, not on intent.
**Implemented in** · `apps/web/src/modality/input/SignInput` (M16)

---

### E5 · Every AI score is overridable by a human, and every override is recorded

A trainer or special educator can override any AI-generated feedback or score. The override,
its author, and its stated reason are persisted.

AI is a co-pilot to the special educator, never a replacement. The override rate is also our
most honest quality metric — see `docs/EXECUTION_PLAN.md` §16.

A trainer's correction is written ONTO the audit record, never over the AI's score.
"The AI said X, the trainer said Y, because Z" is what makes the model answerable;
overwriting would destroy exactly the evidence that matters.

A reason is required, not optional. A specialist forced to articulate a disagreement
usually sharpens it, and that text is the training signal for improving the rubric.

**Enforced by** · `apps/api/tests/test_trainer.py::TestEthicsE5`
**Implemented in** · `apps/api/app/routers/trainer.py` (M14)

---

### E6 · No time-pressure mechanic may gate progression

No countdown timers. No speed bonuses. No "answer within N seconds". No penalty for a long
pause. Recording has no maximum duration.

Difficulty adapts through vocabulary, sentence length, scaffold availability, and interlocutor
patience — **never through speed**.

> **Why.** Time pressure is the fastest way to make this product unusable for a learner with
> dysarthria, with a stammer, with a motor impairment, or with an intellectual disability. It
> excludes three of our five personas in one design decision.

**Enforced by** · `apps/api/tests/test_learning.py` —
`test_derive_grade_cannot_see_timing_at_all`, which asserts the grader has no
timing parameter at all, and `apps/api/tests/test_practice_api.py` —
`test_the_review_endpoint_accepts_no_timing_field`.

---

### E7 · A feature that fails any persona is not shippable

Every feature must work for all five personas in `docs/PERSONAS.md` — P1 low vision, P2 Deaf,
P3 dysarthric with motor impairment, P4 intellectual disability, P5 stammer.

"Works" means completable, not merely renderable.

**Enforced by** · `apps/web/tests/modality/ModalityRouter.test.tsx` (every persona
can receive a lesson) and `apps/web/tests/modality/ModalityInput.test.tsx` (every
persona can answer one), run on every push.
A regression here is a P0 bug, above all other work.

---

## Rules for how we speak to learners

Copy is part of the product, and dignity is part of the specification.

| Never | Instead |
|---|---|
| "Wrong", "Failed", "Incorrect" | "Not quite yet — try this" |
| "Special needs", "Suffers from", "Wheelchair-bound" | "Disabled person" / "Person with a disability" / "Wheelchair user" |
| "Normal speaker", "Native-like" | "Your baseline", "Your best so far" |
| Praise for effort that reads as pity | Specific, factual praise: "Your pause control improved on that one" |
| A raw score during the calibration period | "We're still learning how you speak" |

**Maximum two improvement points per feedback session.** More is not more helpful; it is
demoralising and unusable.

**Strengths are stated before weaknesses. Always.**

---

## Standing obligations

- **Ethics review at every milestone.** MS1–MS6. All three tracks attend. Minuted in `docs/ADR/`.
- **Human-in-the-loop before automation.** Where a decision affects a learner's prospects, a
  human can see it, question it, and change it.
- **No clinical claims.** SAMVAAD is a training tool, not a diagnostic or medical device. It does
  not screen, diagnose, or assess any condition. Concerns route to a human trainer.
- **Co-design, not design-for.** No major feature ships without being tried by disabled users.
  We are not the experts on our users' lives; they are.
- **When a rule and a deadline conflict, the deadline moves.**

---

## Signatures

By committing to this repository you accept these constraints.

| Name | Track | Date |
|---|---|---|
| | T1 — Client & Accessibility | |
| | T2 — Platform & GenAI | |
| | T3 — Speech & ML | |

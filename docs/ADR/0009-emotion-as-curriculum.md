# ADR-0009 · Emotion is curriculum, never measurement

**Status:** Accepted
**Date:** 2026-08-01
**Blueprint:** §2.1, §2.2, §2.3, §7.3 · Appendix A items A1, A2 · signed off 2026-08-01

## Context

The redesign brief asks for **emotion detection**, **confidence estimation** and **body-language
puzzles**. All three collide with Ethics E2, which lists `facial_affect`, `vocal_affect`,
`body_posture`, `motor_stillness` and `gaze` as dimensions the interview rubric is
*structurally prevented* from scoring — a guarantee currently held by four enforcement layers
and a CI invariance gate.

The collision is not merely procedural. Affect recognition has a well-documented failure mode
on exactly this population:

- autistic people whose expression does not map to the training distribution,
- people with facial paralysis, Bell's palsy, Moebius syndrome,
- people with Parkinson's (masked facies) and cerebral palsy,
- people on antipsychotics and several other common medications.

A system that told an autistic learner their tone was "wrong" would not be measuring their
communication. It would be measuring their disability and reporting it as a deficit — which is
the precise harm this product exists to refuse.

Confidence has the same problem by a different route: quiet, flat or hesitant speech is a
disability characteristic for several personas and says nothing at all about how confident the
person feels.

## Decision

**Build emotion as content the learner reads, and as something they tell us. Never as something
we measure about them.**

| Built | Not built |
|---|---|
| `read_the_room` — an illustrated character with an **authored** expression; the learner identifies what they mean | Any inference of emotion from the learner's face |
| Character expression in branching stories, authored per branch as `{character, expression, intensity}` | Any inference of emotion or confidence from the learner's voice |
| Confidence as the existing **self-reported 1–5** PPI dimension | Any score of the learner's own emotional expression |
| Body-language puzzles where the learner **reads** a character's posture | Any puzzle that evaluates the learner's own body |

Three consequences of the framing:

1. **The feature is named "emotion literacy", not "emotion detection"** — in code, in the
   backlog and in the UI. Naming matters here specifically: "emotion detection" sitting in a
   backlog is an instruction to a future engineer to build the forbidden thing.

2. **Self-report is not a downgrade.** For confidence it is the *more* valid instrument, and it
   is what the pilot's confidence outcome measure is based on anyway.

3. **If on-device pose estimation is ever added**, it is a mirror for the learner's private use,
   never a score, and Ethics E4 (video never leaves the device) governs it.

## Consequences

**Good.** A genuinely requested skill for autistic learners ships, and it is one almost nothing
else on the market teaches. The E2 guarantee and its CI gate are untouched. Nothing in the
product ever tells a disabled person that their face or their voice is wrong.

**Cost.** Illustration. Every authored expression is an asset, and the character system is on
the critical path for this mission type — the blueprint flags that as risk R3.

**What would have to change to reverse this.** Amending `docs/ETHICS_CHARTER.md` E2, removing
entries from the rubric exclusion list that CI greps for, and deleting the disfluency-invariance
gate. Deliberately expensive, and deliberately visible in a diff.

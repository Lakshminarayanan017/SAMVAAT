# ADR-0006 · The `pace` dimension measures rhythm steadiness, not speaking speed

**Status:** Accepted
**Date:** 2026-07-31
**Supersedes part of:** ADR-0003's dimension list (the formula is unchanged; the input to it is defined here)

## Context

ADR-0003 fixed five Personal Progress Index dimensions, one of them named `pace`, and gave the
formula `PPI_d = clamp(50 + 15·(x_d − μ_d)/σ_d, 0, 100)`. It did not say what `x_pace` is.

The obvious reading is speaking rate in words per minute. Implementing it that way produces two
defects that are not obvious until you write the number down next to a persona.

**Defect 1 — it rewards hurrying.** With `x_pace` = words per minute, speaking faster than your
own baseline raises your score. That is a speed bonus. Ethics rule E6 forbids time-pressure
mechanics because they exclude P3, P4 and P5 in a single design decision, and a scoring dimension
that pays out for speed is a time-pressure mechanic that happens not to have a clock on screen.
It is arguably worse than a visible timer, because the learner cannot see what is being asked of
them.

**Defect 2 — it scores a fixed characteristic.** P3 (Arjun, cerebral palsy with dysarthria) speaks
at roughly 60 words per minute and will for the rest of his life. Speaking rate in dysarthria is
not a skill gap that practice closes; it is motor function. Baseline-relative scoring protects him
from being compared to anyone else, but it does not stop the dimension from asking him to practise
something he cannot change. A dimension nobody can move is a dimension that teaches the learner
the number is noise.

Meanwhile there is a real, teachable, listener-facing property nearby: whether speech comes out in
evenly sized chunks. Erratic chunking is what actually makes an utterance hard to follow, it is
independent of absolute speed, and it does respond to practice — pausing strategies, breath
support and phrasing all move it.

## Decision

**`x_pace` is rhythm steadiness, computed from the coefficient of variation of the durations of
continuous speaking runs within the utterance.**

```
runs   = durations of continuous speech, split at pauses >= 250 ms
cv     = stdev(runs) / mean(runs)
x_pace = 100 / (1 + cv)          # bounded (0, 100], higher = more even
```

Undefined, and therefore omitted from the attempt, when there is fewer than one pause: a single
unbroken run has no rhythm to be steady about, and scoring it 100 would reward "did not pause",
which is exactly the thing several of our learners physically cannot do.

Absolute speaking rate is still **measured** — `speech_rate_wpm` and `articulation_rate_wpm` are on
`ProsodyFeatures`, and the learner can see them on their dashboard as facts about their own speech.
They are simply not scored.

## Consequences

**Easy**
- Two learners with identical evenness and a four-fold difference in speed measure identically.
  There is a test for exactly this.
- Nothing in the index pays out for going faster, so E6 holds at the level of the maths rather than
  at the level of the UI.
- The dimension is teachable. Pausing and phrasing strategies from the coaching library move it,
  which means the coaching cue and the number finally point the same way.

**Hard**
- "Pace" is now a slightly misleading label for what is measured. Kept because it is the word the
  execution plan, the CAP `scoring_weights` schema and the learner-facing copy already use, and
  renaming a persisted schema field to improve a metaphor is a poor trade. The learner-facing label
  is "how evenly your speech flowed", which is accurate.
- Short single-phrase drills often produce no pause and therefore no `pace` measurement. The
  composite renormalises over what is present, so this costs the learner nothing, but it does mean
  the dimension populates mainly from role-play and interview answers rather than from flashcards.
- Rhythm steadiness is a less familiar quantity than words per minute, so the trainer dashboard has
  to explain it. That explanation exists.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Words per minute against own baseline | Rewards speed (E6) and scores motor function as though it were skill. |
| Distance from a "comfortable range" of 120–150 wpm | A reference-speaker comparison with extra steps. Violates E1 outright. |
| Distance from the learner's own established rate, in either direction | Defensible, and considered seriously. Rejected because it punishes deliberate slowing, which is the single most common strategy the coaching library recommends — the learner would follow the advice and watch the score fall. |
| Drop the `pace` dimension entirely | Loses a genuinely teachable property, and leaves a field in the persisted CAP schema with nothing behind it. |

## Related

- Implemented in `services/speech/pipeline/measures.py::rhythm_steadiness`
- Measured in `services/speech/pipeline/prosody.py` (`speaking_runs_seconds`)
- Enforced by `services/speech/tests/test_measures.py::TestRhythmSteadiness::test_speed_does_not_enter_the_measure`

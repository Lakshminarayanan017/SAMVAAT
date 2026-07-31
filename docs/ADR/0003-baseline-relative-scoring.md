# ADR-0003 · Scoring is baseline-relative, never reference-speaker-relative

**Status:** Accepted
**Date:** 2026-07-31

## Context

Standard pronunciation assessment computes similarity between the learner's speech and a
neurotypical native reference. Applied to our users this is not merely inaccurate — it is
actively harmful. A learner with dysarthria, a cleft palate, deaf speech, or a stammer will
score badly on day one and on day four hundred, no matter how much they improve.

The tool then reports, daily, that the learner is failing at being non-disabled. They leave.
This is the single largest reason existing speech-training apps do not work for this population.

## Decision

**All learner-facing scores are computed as a delta from the learner's own rolling baseline.**

For each dimension `d` in {intelligibility, pronunciation, pace, fluency, confidence}:

```
μ_d, σ_d  = EWMA mean and standard deviation over the learner's own attempts
PPI_d(t)  = clamp(50 + 15 · (x_d(t) − μ_d) / max(σ_d, ε), 0, 100)
```

Supporting rules:

- **Calibration period** — for the first ~10 attempts, show no numeric score at all.
  Show "we're still learning how you speak."
- **Inspectable baseline** — the learner can always see the underlying figure:
  *"your baseline for pace was 92 wpm; today you were 104 wpm."*
- **Profile-weighted composite** — dimension weights come from the Communication Ability
  Profile. For a learner with a stammer, `fluency` is down-weighted and `intelligibility`
  up-weighted. The weighting is visible to the learner and the trainer, never hidden.
- **Disfluency produces coaching cues, never deductions.** A detected block emits
  `{event, timestamp, suggested_strategy}` from an SLP-reviewed strategy library.
- **Raw Goodness-of-Pronunciation is never surfaced.** It is an input to the PPI and nothing else.

## Consequences

**Easy**
- Progress is always achievable, so the product retains the users it exists for.
- The learner-facing chart — your line rising above your own baseline — is genuinely motivating
  and is the most persuasive screen in the product.
- Cross-learner comparison becomes meaningless by construction, which is a feature: it kills any
  temptation to build a leaderboard.

**Hard**
- Cold start. A brand-new learner has no baseline, hence the calibration period.
- Baseline drift. If the EWMA tracks too fast, improvement is absorbed and the score flatlines.
  `α` is tuned so the baseline moves over ~3 weeks, not ~3 days.
- Bad-day sensitivity. Illness, fatigue, or anxiety move the score. Mitigated by smoothing and
  by never showing a single attempt as a verdict.
- Institutions will ask for absolute, comparable scores. We will decline, and explain why.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Reference-speaker similarity | Guarantees a permanent low score for disabled learners. The problem we exist to fix. |
| Disability-group-normed scoring | Requires assigning learners to a diagnostic category and comparing them to it. Ethically worse, and diagnostically wrong. |
| No scoring at all | Loses the motivational and diagnostic value, and institutions cannot measure outcomes |

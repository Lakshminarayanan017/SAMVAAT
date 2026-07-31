# ADR-0002 · Every input modality normalises to a single `LearnerResponse`

**Status:** Accepted
**Date:** 2026-07-31

## Context

Learners answer by speaking, typing, signing to a camera, tapping picture symbols, or driving a
two-switch scanner. Downstream we need to score the answer, schedule the next card, feed the
recommendation engine, and render progress on three dashboards.

The naive design branches on input mode at every one of those points. That yields five parallel
implementations of scoring, five of scheduling, five of analytics — and four of them will be
under-tested, because the team's own devices default to typing.

## Decision

**Every input adapter emits the same `LearnerResponse`, carrying a normalised `canonical_text`.**

```
SpeechInput    → ASR              → canonical_text
TextInput      → normalise        → canonical_text
SignInput      → sign classifier  → canonical_text
AACBoardInput  → symbol→text      → canonical_text
SwitchScanInput→ selection→text   → canonical_text
```

Mode-specific data lives in a `raw` sub-object. Only genuinely acoustic analytics — GOP,
prosody, disfluency — are conditional on `input_mode == "speech"`.

## Consequences

**Easy**
- One scoring engine, one scheduler, one recommender, one dashboard serve all five personas.
- A non-verbal learner completes a *mock interview* — a first-class path, not a degraded one.
- Test surface collapses: most logic is tested once against `canonical_text`.

**Hard**
- Normalisation quality becomes critical and is not uniform. ASR on dysarthric speech and sign
  classification are both lossy in ways typing is not.
- We must attach a confidence to `canonical_text` and never treat a low-confidence
  transcription as a definite wrong answer. Below threshold we offer confirmation, not judgement.
- AAC and sign vocabularies are bounded, so `canonical_text` from those modes is drawn from a
  smaller space. Scoring must not read that as a poorer answer.

**Accepted cost:** real complexity pushed into the input adapters, in exchange for removing it
from everything downstream.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Branch on input mode downstream | Five parallel implementations; four inevitably under-tested |
| Score each modality with its own engine | Makes cross-modality progress incomparable, so the dashboards become meaningless |
| Accept only text and speech | Excludes P2 and P4 entirely — the users this project exists for |

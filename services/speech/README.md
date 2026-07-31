# services/speech — speech analysis service

**Modules M5–M8** · FastAPI · Python 3.10+

ASR, forced alignment, Goodness-of-Pronunciation, prosody, disfluency detection, and the
**Personal Progress Index** — the baseline-relative score that is the ethical core of the
product ([ADR-0003](../../docs/ADR/0003-baseline-relative-scoring.md)).

Deployed separately because PyTorch, the forced aligner and openSMILE make this container
multi-gigabyte with slow cold starts, and because it scales as CPU-bound bursts rather than
steady I/O ([ADR-0004](../../docs/ADR/0004-three-services-not-five.md)).

---

## Run it

```bash
python -m venv .venv
.venv/Scripts/activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn service.main:app --reload --port 8100

pytest                          # tests
python -m eval.harness --set atypical    # the eval table for your PR
```

---

## The pipeline

```
audio(16k) ─┬─> preprocess ──> ASR ────────────────> transcript + confidence
            ├─> G2P(target) ───────────────────────> expected phonemes
            ├─> forced alignment ──────────────────> phoneme boundaries
            ├─> acoustic posteriors ──> GOP ───────> per-phoneme pronunciation
            ├─> prosody ───────────────────────────> rate, pauses, F0, energy
            └─> disfluency ────────────────────────> events + coaching cues
                                          ↓
                          Personal Progress Index (baseline-relative)
```

Each stage is a pure function over the previous stage's output, so any stage can be
evaluated in isolation by the harness.

**Two-track ASR.** A *free* recognition pass answers "what did they actually say?"
(intelligibility) and a *forced* pass against the target text answers "how well did they say
the intended thing?" (GOP). Conflating the two is the classic bug in this kind of pipeline.

---

## `/capabilities` — honest degradation

Every pipeline flag starts `false` and flips only when the module implementing it lands
**with a passing eval run**. The client reads this endpoint rather than assuming, so it can
say *"practised offline — detailed feedback will arrive when you reconnect"* instead of
showing a learner a spinner that never resolves.

Flipping a flag without a passing eval is a review failure.

---

## The evaluation harness

`eval/harness.py` was written **before** the pipeline it measures. A model without a frozen
eval set and a regression gate is a model nobody can safely change.

**Every speech PR includes the harness table, before and after.**

Two things make this harness different from a normal ML eval:

1. **Results are always reported per speaker, never only as a mean.** A model can post an
   excellent average while failing every dysarthric speaker in the set — and those are
   precisely the users this product exists for. The mean is printed last and labelled
   *context only*.
2. **Fairness checks are gates, not diagnostics.** A model that improves WER but fails the
   monotonicity or invariance check does not ship.

| Module | Metric | Bar |
|---|---|---|
| M6 | `gop_expert_correlation` | Spearman ρ ≥ 0.60 vs SLP ratings |
| M7 | `disfluency_macro_f1` | ≥ 0.65 on SEP-28k held-out |
| M7 | `ppi_monotonicity` | Improving attempts must produce a rising PPI |
| M7 | `ppi_disfluency_invariance` | **The proof of ADR-0003** — two synthetic speakers with identical content and improvement, one with injected disfluency, must produce indistinguishable PPI trajectories |
| M8 | `wer_relative_reduction` | ≥ 25% relative vs base Whisper, **per speaker** |

---

## Ethics rules enforced here

| Rule | How |
|---|---|
| **E1** — no comparison to a non-disabled reference speaker | Raw GOP is an internal signal only. It is never returned to a client; only the PPI is surfaced. |
| **E3** — raw audio deleted within 24h | This service holds audio for the duration of a request and never persists it. |
| **Disfluency → coaching, never deduction** | The disfluency stage emits `{event, timestamp, suggested_strategy}` from an SLP-reviewed strategy library. No code path converts an event into a score deduction. |

---

## Datasets

See [`docs/EXECUTION_PLAN.md` §9.3](../../docs/EXECUTION_PLAN.md). **UASpeech** and the
**Speech Accessibility Project** need access applications with multi-week turnaround —
submit them in week 1, not when you need the data. **SEP-28k** and **INCLUDE** are
downloadable now.

`data/` and `artifacts/` are gitignored. Models live in the MLflow registry, not in git.

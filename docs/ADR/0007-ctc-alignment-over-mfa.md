# ADR-0007 · CTC forced alignment over a phoneme model, not the Montreal Forced Aligner

**Status:** Accepted
**Date:** 2026-07-31

## Context

Goodness of Pronunciation needs two things: the time boundaries of each expected phoneme, and the
acoustic model's per-phoneme posteriors over those frames. The execution plan (M6) named the
Montreal Forced Aligner as the first choice with `torchaudio` CTC segmentation as a lighter
fallback, and asked for the decision to be recorded as an ADR once both had been measured.

The two options differ in more than precision.

**MFA** is a Kaldi-based toolkit. It is more precise at boundary placement — this is not in
dispute. It also requires a Kaldi install, a pronunciation dictionary, a pretrained acoustic model
per language, and a working directory it can write to. Containerising it reliably is a known
source of pain, and the resulting image does not fit comfortably in the free tier this project is
committed to running on. Critically, MFA gives boundaries but does not hand back frame-level
posteriors in a form the GOP definition can consume, so a second forward pass through a different
model is needed anyway — and then the boundaries and the posteriors come from two different
acoustic models, which is precisely the mismatch that produces confident nonsense.

**CTC forced alignment** over `facebook/wav2vec2-lv-60-espeak-cv-ft` produces both quantities from
one forward pass through one model. The model emits IPA phoneme posteriors directly, which is the
exact quantity the GOP formula is written over.

## Decision

**Forced alignment is `torchaudio.functional.forced_align` over the log-posteriors of a
phoneme-level wav2vec2 CTC model, and the same posterior matrix is passed straight to the GOP
scorer.**

Consequences that follow from "one model, one pass":

- Boundaries and posteriors are guaranteed to be about the same acoustic evidence.
- The expensive stage runs once per attempt rather than twice, which matters on a CPU host.
- CMUdict speaks ARPAbet and the model speaks IPA, so a single audited mapping table lives in
  `pipeline/g2p.py::arpabet_to_ipa`. A test asserts it covers the whole ARPAbet inventory —
  a silent gap there would align every utterance against the wrong targets.

Phones outside the model's vocabulary are **dropped from the alignment**, not aligned against an
arbitrary column, and `gop.score_alignment` skips them rather than scoring them zero. A zero reads
as a perfect pronunciation of a sound the model cannot even represent.

Alignment quality is returned as a confidence on the `Alignment`, and `gop.MIN_ALIGNMENT_SCORE`
gates whether a pronunciation score is produced at all. A bad alignment does not produce a bad
score; it produces no score, and the Personal Progress Index omits the dimension.

## Consequences

**Easy**
- One dependency (`torchaudio` + `transformers`), no Kaldi, no writable working directory, no
  per-language acoustic model to ship. The container is buildable on a free tier.
- The whole path is exercisable in tests, because `gop.py` is pure maths over a posterior matrix
  and the matrix can be constructed by hand.
- Swapping the acoustic model is a constant change plus a re-run of the eval harness.

**Hard**
- Boundary precision is lower than MFA's. This matters most for very short phones, which is why
  `MIN_PHONE_DURATION_S` drops phones under 20 ms rather than scoring alignment artefacts.
- The model is multilingual and English-heavy rather than Indian-English-specific. Accent effects
  on the posteriors are real — and are precisely why raw GOP never reaches a learner and only
  enters the baseline-relative index (E1, ADR-0003).
- We inherit whatever `torchaudio` decides to do with `forced_align`; the call is isolated behind
  `backends.align` so a future change is one function.

## Revisit when

- The eval harness shows GOP–expert correlation below the ρ ≥ 0.6 bar on the labelled subset, and
  boundary error is identified as the cause rather than the acoustic model.
- An Indian-English phoneme model of comparable size becomes available.

Both are measurable with the harness that already exists, which is the point of having built it
before the pipeline it evaluates.

## Related

- `services/speech/pipeline/backends.py::align`
- `services/speech/pipeline/gop.py` (unchanged by this decision — it consumes a matrix)
- `services/speech/eval/harness.py` target `gop_expert_correlation`

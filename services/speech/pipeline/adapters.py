"""Personalised ASR adapters (M8).

The most technically novel part of this project, and the one that decides
whether the speech half of the product works for P3 at all. Base Whisper's word
error rate on dysarthric speech routinely exceeds 50%. At that rate every drill
tells a learner they said the wrong thing when they did not, and no amount of
kind copy makes that usable.

FOUR STAGES, IN ORDER OF COST — IMPLEMENT AND SHIP IN THIS ORDER
----------------------------------------------------------------
  (a) Vocabulary biasing.      Free. No GPU. Already live in `backends.transcribe`.
  (b) Phrase-set shallow fusion. Cheap. Rescoring against the phrase bank.
  (c) LoRA adapter fine-tune.  ~2-5 MB per learner, trained on their own 30
                               enrolment clips. This module loads and serves it.
  (d) Pooled cold-start.       [V2] cluster learners, start from the cluster.

Stages (a) and (b) deliver a real, demoable improvement with no GPU at all. That
matters more than it sounds: it means the feature is not blocked on a training
run, and a learner gets a better experience on their first session rather than
after thirty.

THE GUARDRAIL THAT MATTERS
--------------------------
An adapter is only ever deployed if it beats base ASR **on that learner's own
held-out clips**. Personalisation that makes recognition worse is not a
degraded feature, it is an actively harmful one — and "we fine-tuned on your
voice" makes it feel like the learner's fault. `evaluate_adapter` is the gate,
and `AdapterRecord.deployed` is false until it passes.

WHAT IS NOT HERE
----------------
The training loop. It lives in `training/train_asr_adapter.py`, runs on Colab or
a serverless GPU, and writes an adapter directory plus an eval record. This
module is the serving half: it loads what training produced, and it refuses to
load anything that has not passed the guardrail.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Protocol

log = logging.getLogger("samvaad.speech.adapters")

#: An adapter must beat base ASR by at least this much, relatively, before it is
#: served. Sourced from docs/EXECUTION_PLAN.md §9.4. Below it the improvement is
#: inside the noise of a 30-clip held-out set, and deploying on noise means some
#: learners get worse recognition and are told it is better.
MIN_RELATIVE_WER_REDUCTION = 0.25

#: Phrases in the enrolment set. Drawn from the phrase bank so enrolment is
#: itself useful practice rather than a chore standing between the learner and
#: the product.
ENROLMENT_PHRASE_COUNT = 30

#: Adapters loaded into memory at once. Each is small, but a busy host with a
#: hundred concurrent learners would otherwise hold a hundred merged models.
ADAPTER_CACHE_SIZE = 8


class AdapterUnavailable(RuntimeError):
    """Raised when an adapter cannot be loaded. Callers fall back to base ASR."""


@dataclass(frozen=True)
class EnrolmentProgress:
    """How far through enrolment a learner is.

    Resumable and skippable, always. Enrolment is thirty recordings; for a
    learner with dysarthria that is real physical effort, and a flow that loses
    progress or blocks the product until it is finished would simply not be
    completed.
    """

    user_id: str
    completed: int = 0
    required: int = ENROLMENT_PHRASE_COUNT
    #: Block ids already recorded, so a resumed session does not repeat them.
    recorded_block_ids: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        return self.completed >= self.required

    @property
    def fraction(self) -> float:
        return min(1.0, self.completed / self.required) if self.required else 1.0

    def message(self) -> str:
        """Learner-facing progress. Never a countdown, never a deadline."""
        if self.is_complete:
            return "Enrolment finished. We can start tuning the app to your voice."
        remaining = self.required - self.completed
        return (
            f"{self.completed} of {self.required} recorded. "
            f"{remaining} to go, whenever you like — this saves as you go."
        )


@dataclass(frozen=True)
class AdapterEvaluation:
    """The before/after that decides whether an adapter is served.

    Held-out, per learner, and persisted. `wer_after < wer_before` is not a
    nice-to-have; it is the deployment condition.
    """

    wer_before: float
    wer_after: float
    held_out_utterances: int
    evaluated_at: datetime

    @property
    def relative_reduction(self) -> float:
        if self.wer_before <= 0:
            return 0.0
        return (self.wer_before - self.wer_after) / self.wer_before

    @property
    def passes_guardrail(self) -> bool:
        return (
            self.wer_after < self.wer_before
            and self.relative_reduction >= MIN_RELATIVE_WER_REDUCTION
            and self.held_out_utterances >= 5
        )

    def learner_message(self) -> str:
        """The delightful moment, and an honest one.

        Phrased as the app improving, not the learner. "You are 34% clearer"
        would be false and would also be the exact framing this product exists
        to refuse.
        """
        percent = round(self.relative_reduction * 100)
        if not self.passes_guardrail:
            return "We are still learning your voice. Nothing has changed yet."
        return f"The app now understands you about {percent}% better than before."


@dataclass(frozen=True)
class AdapterRecord:
    """One learner's adapter, and everything needed to trust it."""

    user_id: str
    #: Directory holding the PEFT adapter weights and config.
    path: Path
    base_model: str
    trained_at: datetime
    evaluation: AdapterEvaluation | None = None
    #: Set only after the guardrail passes. The loader checks this, not the
    #: presence of the files — weights on disk are not permission to serve them.
    deployed: bool = False
    #: Confirmed transcriptions seen since training, driving the retrain trigger.
    new_samples_since_training: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def should_retrain(self, threshold: int = 20) -> bool:
        return self.new_samples_since_training >= threshold


class AdapterRegistry(Protocol):
    """The seam the object-storage implementation fills in M17."""

    def get(self, user_id: str) -> AdapterRecord | None: ...

    def save(self, record: AdapterRecord) -> None: ...

    def list_deployed(self) -> list[AdapterRecord]: ...


class FileAdapterRegistry:
    """Adapters on a mounted volume, with a JSON sidecar per learner.

    A directory rather than a database because the artefacts are files anyway
    and the API gateway owns the database (ADR-0004). The sidecar carries the
    evaluation, so a host that has the weights but not the eval record refuses
    to serve them — which is the correct behaviour after a partial restore.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _sidecar(self, user_id: str) -> Path:
        return self.root / user_id / "adapter.json"

    def get(self, user_id: str) -> AdapterRecord | None:
        sidecar = self._sidecar(user_id)
        if not sidecar.exists():
            return None

        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            log.warning("adapter sidecar for %s is unreadable (%s)", user_id, error)
            return None

        evaluation = payload.get("evaluation")

        return AdapterRecord(
            user_id=user_id,
            path=self.root / user_id,
            base_model=payload["base_model"],
            trained_at=datetime.fromisoformat(payload["trained_at"]),
            evaluation=(
                AdapterEvaluation(
                    wer_before=evaluation["wer_before"],
                    wer_after=evaluation["wer_after"],
                    held_out_utterances=evaluation["held_out_utterances"],
                    evaluated_at=datetime.fromisoformat(evaluation["evaluated_at"]),
                )
                if evaluation
                else None
            ),
            deployed=bool(payload.get("deployed", False)),
            new_samples_since_training=int(payload.get("new_samples_since_training", 0)),
            metadata=payload.get("metadata", {}),
        )

    def save(self, record: AdapterRecord) -> None:
        directory = self.root / record.user_id
        directory.mkdir(parents=True, exist_ok=True)

        payload = {
            "base_model": record.base_model,
            "trained_at": record.trained_at.isoformat(),
            "evaluation": (
                {
                    **asdict(record.evaluation),
                    "evaluated_at": record.evaluation.evaluated_at.isoformat(),
                }
                if record.evaluation
                else None
            ),
            "deployed": record.deployed,
            "new_samples_since_training": record.new_samples_since_training,
            "metadata": record.metadata,
        }

        self._sidecar(record.user_id).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def list_deployed(self) -> list[AdapterRecord]:
        if not self.root.exists():
            return []

        records = (self.get(child.name) for child in self.root.iterdir() if child.is_dir())
        return [record for record in records if record and record.deployed]


def registry() -> AdapterRegistry | None:
    """The configured registry, or None when personalisation is switched off."""
    from service.config import get_settings

    directory = get_settings().adapters_dir
    return FileAdapterRegistry(directory) if directory else None


def promote(record: AdapterRecord, evaluation: AdapterEvaluation) -> AdapterRecord:
    """Attach an evaluation and decide whether the adapter may be served.

    The single place `deployed` is allowed to become true. Keeping that decision
    in one function means the guardrail cannot be bypassed by a caller who
    constructs an `AdapterRecord` optimistically.
    """
    from dataclasses import replace

    deployed = evaluation.passes_guardrail

    if not deployed:
        log.info(
            "adapter for %s not deployed: WER %.3f -> %.3f (%.1f%% relative, need %.0f%%)",
            record.user_id,
            evaluation.wer_before,
            evaluation.wer_after,
            evaluation.relative_reduction * 100,
            MIN_RELATIVE_WER_REDUCTION * 100,
        )

    return replace(record, evaluation=evaluation, deployed=deployed)


@lru_cache(maxsize=ADAPTER_CACHE_SIZE)
def _load_peft(adapter_path: str, base_model: str):
    """Merge an adapter into a copy of the base model, cached by path.

    Merging rather than keeping the adapter live: a merged model runs at base
    speed, and the per-request cost of `peft`'s wrapper is measurable on the CPU
    host we deploy to. The cache bound is what keeps a hundred concurrent
    learners from becoming a hundred resident models.
    """
    from peft import PeftModel
    from transformers import AutoProcessor, WhisperForConditionalGeneration
    from transformers import pipeline as hf_pipeline

    log.info("loading adapter %s over %s", adapter_path, base_model)

    model = WhisperForConditionalGeneration.from_pretrained(base_model)
    model = PeftModel.from_pretrained(model, adapter_path).merge_and_unload()
    model.eval()

    processor = AutoProcessor.from_pretrained(base_model)

    return hf_pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
    )


def apply_adapter(base_pipeline, user_id: str):
    """This learner's personalised pipeline, or the base one.

    Never raises for an ordinary "no adapter" case. A learner without an adapter
    is the normal state — most learners will never have one, and every one of
    them must still be able to record.
    """
    store = registry()
    if store is None:
        return base_pipeline

    record = store.get(user_id)
    if record is None or not record.deployed:
        return base_pipeline

    if not record.path.exists():
        log.warning("adapter record for %s points at a missing directory", user_id)
        return base_pipeline

    return _load_peft(str(record.path), record.base_model)


# ── Evaluation ───────────────────────────────────────────────────────────────


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Standard WER over word tokens.

    Shared by the training script and the serving guardrail so the number that
    justified deploying an adapter is computed the same way as the number that
    monitors it. Two implementations of WER always drift, and the drift shows up
    as an adapter that "passed" and does not help.
    """
    from pipeline.measures import _word_edit_distance, _words

    reference_words = _words(reference)
    if not reference_words:
        return 0.0

    return _word_edit_distance(_words(hypothesis), reference_words) / len(reference_words)


def evaluate_adapter(
    pairs_before: list[tuple[str, str]],
    pairs_after: list[tuple[str, str]],
    now: datetime | None = None,
) -> AdapterEvaluation:
    """Compare base and adapted transcriptions on the same held-out clips.

    Args:
        pairs_before: (reference, base hypothesis) per held-out utterance.
        pairs_after: (reference, adapted hypothesis) for the SAME utterances.

    The pairing is positional and the caller must preserve order — comparing an
    adapter against a different set of clips than the base is the easiest way to
    produce a improvement that does not exist.
    """
    if len(pairs_before) != len(pairs_after):
        raise ValueError(
            "before/after evaluations must cover the same held-out utterances; "
            f"got {len(pairs_before)} and {len(pairs_after)}"
        )

    def mean_wer(pairs: list[tuple[str, str]]) -> float:
        if not pairs:
            return 0.0
        return sum(word_error_rate(ref, hyp) for ref, hyp in pairs) / len(pairs)

    return AdapterEvaluation(
        wer_before=mean_wer(pairs_before),
        wer_after=mean_wer(pairs_after),
        held_out_utterances=len(pairs_before),
        evaluated_at=now or datetime.now(timezone.utc),
    )


def select_enrolment_phrases(
    blocks: list[dict],
    count: int = ENROLMENT_PHRASE_COUNT,
) -> list[dict]:
    """Choose the enrolment set for phonetic coverage.

    Greedy set cover over phonemes rather than a random sample. Thirty random
    phrases from a workplace corpus over-represent the same handful of common
    words; thirty chosen for coverage exercise the sounds the adapter actually
    needs to learn, which is the difference between an adapter that helps and
    one that does not clear the guardrail.

    Blocks without a phoneme string are eligible but never preferred: they carry
    no coverage information, so they can only be filler.
    """
    remaining = list(blocks)
    chosen: list[dict] = []
    covered: set[str] = set()

    def gain(block: dict, seen: frozenset[str]) -> tuple[int, int]:
        phonemes = set((block.get("representations", {}).get("phonemes") or "").split())
        # Shorter phrases first among equal gain: enrolment is physical effort,
        # and a learner who tires is a learner who stops.
        return len(phonemes - seen), -len(block.get("canonical_text", ""))

    while remaining and len(chosen) < count:
        seen = frozenset(covered)
        best = max(remaining, key=lambda block: gain(block, seen))
        best_gain, _ = gain(best, seen)

        if best_gain == 0 and covered:
            # Nothing new left to cover. Fill from the easiest remaining rather
            # than stopping short of the required count.
            remaining.sort(key=lambda b: (b.get("difficulty", 3), len(b.get("canonical_text", ""))))
            chosen.extend(remaining[: count - len(chosen)])
            break

        chosen.append(best)
        covered |= set((best.get("representations", {}).get("phonemes") or "").split())
        remaining.remove(best)

    return chosen[:count]

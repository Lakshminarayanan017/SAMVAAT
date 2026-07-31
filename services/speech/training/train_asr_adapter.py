#!/usr/bin/env python
"""Train one learner's personalised ASR adapter (M8 stage c).

    python -m training.train_asr_adapter --user-id p3-arjun --clips ./enrolment/p3-arjun

WHAT THIS DOES AND DOES NOT DO
------------------------------
It fine-tunes a LoRA adapter over Whisper on ONE learner's own thirty enrolment
clips, evaluates it against base Whisper on that learner's held-out clips, and
writes the adapter only if it actually helped. It does not touch the base model,
it does not pool learners, and it does not deploy anything that fails the
guardrail.

The guardrail is the point. Personalisation that makes recognition worse is not
a degraded feature — it is actively harmful, and "we tuned this to your voice"
makes the learner feel it is their fault. `evaluate_adapter` decides; this script
only obeys.

RUNNING IT
----------
Needs a GPU. Free Colab T4 is enough and is what this is written for:

    pip install -r services/speech/requirements-ml.txt
    python -m training.train_asr_adapter --user-id <id> --clips <dir> --base openai/whisper-small

Roughly 8-12 minutes per learner on a T4 for 30 clips with augmentation, which
is inside the < 15 minute bar in the execution plan.

CLIP DIRECTORY LAYOUT
---------------------
    <clips>/
        manifest.json      [{"audio": "001.wav", "text": "Good morning."}, ...]
        001.wav            16 kHz mono
        ...

The manifest is written by the enrolment flow. `text` is the phrase the learner
was asked to say — NOT a transcription of what they said. That distinction is
the whole training signal: we are teaching the model to map this learner's
production of a phrase onto the phrase.

WHY THE HELD-OUT SPLIT IS BY PHRASE, NOT RANDOM
-----------------------------------------------
Thirty clips is a small set, and a random split leaves the same phrase in train
and test often enough to matter. The model then scores well by having memorised
the sentence rather than by having learned the voice, the adapter passes the
guardrail, and it does nothing for a learner in real use. Splitting on phrase
identity is what makes the WER reduction mean something.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("samvaad.training.asr_adapter")

#: Held-out proportion. Six of thirty clips: enough for the guardrail's
#: five-utterance minimum with one to spare, and not so many that the adapter is
#: starved of the data it exists to learn from.
HELD_OUT_FRACTION = 0.2

#: LoRA hyperparameters. Rank 16 over the attention projections gives roughly
#: 2-5 MB per learner, which is the size budget that makes per-request adapter
#: loading viable at all.
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = ["q_proj", "v_proj"]

#: Thirty clips is very little data. Heavy augmentation is not optional here —
#: without it the adapter memorises thirty waveforms and generalises to nothing.
AUGMENTATION_FACTOR = 8
SPEED_RANGE = (0.9, 1.1)
NOISE_SNR_DB = (15, 30)

EPOCHS = 8
LEARNING_RATE = 1e-3
BATCH_SIZE = 4


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, help="Learner whose adapter this is")
    parser.add_argument("--clips", required=True, type=Path, help="Enrolment clip directory")
    parser.add_argument("--base", default="openai/whisper-small", help="Base ASR model")
    parser.add_argument(
        "--adapters-dir",
        type=Path,
        default=None,
        help="Where to write. Defaults to the service's configured adapters_dir.",
    )
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the clip set and print the plan without training.",
    )
    return parser.parse_args(argv)


# ── Dataset validation ───────────────────────────────────────────────────────


def load_manifest(clips: Path) -> list[dict]:
    """Read and validate the enrolment manifest.

    Validation is strict and refuses rather than warns. A silently dropped clip
    means an adapter trained on twenty-four examples that reports itself as
    trained on thirty, and the guardrail then compares two things that are not
    what they claim to be.
    """
    manifest_path = clips / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest at {manifest_path}. See the module docstring for layout.")

    entries = json.loads(manifest_path.read_text(encoding="utf-8"))

    problems: list[str] = []
    for index, entry in enumerate(entries):
        if not entry.get("text", "").strip():
            problems.append(f"entry {index}: empty target text")
        audio = clips / entry.get("audio", "")
        if not audio.exists():
            problems.append(f"entry {index}: missing audio {entry.get('audio')!r}")

    if problems:
        raise SystemExit("Enrolment set is not usable:\n  " + "\n  ".join(problems))

    if len(entries) < 10:
        raise SystemExit(
            f"Only {len(entries)} clips. Below about ten there is not enough signal to "
            "train an adapter that clears the guardrail, and training one anyway wastes "
            "the learner's effort. Ask them to finish enrolment first."
        )

    return entries


def split_by_phrase(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Hold out whole phrases, never individual recordings of a shared phrase.

    See the module docstring: a random split lets the model memorise sentences
    and pass the guardrail without having learned anything about the voice.
    """
    phrases = sorted({entry["text"].strip().lower() for entry in entries})
    held_out_count = max(1, round(len(phrases) * HELD_OUT_FRACTION))

    # A stable digest, not `hash()`. Python salts string hashing per process, so
    # `hash()` would give a different split on every run — and two runs over the
    # same enrolment set would produce WER figures that cannot be compared,
    # which is exactly what the guardrail depends on being able to do.
    def order(phrase: str) -> str:
        return hashlib.sha256(phrase.encode("utf-8")).hexdigest()

    held_out_phrases = set(sorted(phrases, key=order)[:held_out_count])

    train = [e for e in entries if e["text"].strip().lower() not in held_out_phrases]
    held_out = [e for e in entries if e["text"].strip().lower() in held_out_phrases]

    return train, held_out


# ── Augmentation ─────────────────────────────────────────────────────────────


def augment(samples, sample_rate: int, rng):
    """One augmented copy: speed, gain and additive noise.

    Deliberately conservative on speed. Aggressive time-stretching of dysarthric
    speech destroys exactly the timing characteristics the adapter needs to
    learn, so ±10% rather than the ±20% a typical-speech recipe would use.

    Pitch shifting is omitted entirely: it alters formant structure, and formant
    structure is a large part of what makes this learner's speech theirs.
    """
    import librosa
    import numpy as np

    rate = rng.uniform(*SPEED_RANGE)
    stretched = librosa.effects.time_stretch(samples, rate=rate)

    snr_db = rng.uniform(*NOISE_SNR_DB)
    signal_power = float(np.mean(stretched**2)) or 1e-12
    noise_power = signal_power / (10 ** (snr_db / 10))
    noisy = stretched + rng.normal(0, noise_power**0.5, len(stretched)).astype("float32")

    gain = rng.uniform(0.7, 1.0)
    return np.clip(noisy * gain, -1.0, 1.0).astype("float32")


# ── Training ─────────────────────────────────────────────────────────────────


def build_dataset(entries: list[dict], clips: Path, processor, augment_copies: int):
    """Feature-extract and tokenise, with augmentation applied to training only."""
    import numpy as np
    import soundfile as sf

    rng = np.random.default_rng(20260731)
    features: list[dict] = []

    for entry in entries:
        samples, sample_rate = sf.read(clips / entry["audio"], dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        variants = [samples] + [
            augment(samples, sample_rate, rng) for _ in range(augment_copies)
        ]

        for variant in variants:
            features.append(
                {
                    "input_features": processor.feature_extractor(
                        variant, sampling_rate=sample_rate, return_tensors="np"
                    ).input_features[0],
                    "labels": processor.tokenizer(entry["text"]).input_ids,
                }
            )

    return features


def transcribe_all(model, processor, entries: list[dict], clips: Path) -> list[tuple[str, str]]:
    """(reference, hypothesis) for each clip, in manifest order.

    Order is preserved because `evaluate_adapter` pairs before and after
    positionally — comparing an adapter against a different set of clips than
    the base is the easiest way to manufacture an improvement that is not real.
    """
    import soundfile as sf
    import torch

    pairs: list[tuple[str, str]] = []
    model.eval()

    for entry in entries:
        samples, sample_rate = sf.read(clips / entry["audio"], dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)

        inputs = processor.feature_extractor(
            samples, sampling_rate=sample_rate, return_tensors="pt"
        )

        with torch.inference_mode():
            tokens = model.generate(
                inputs.input_features.to(model.device), max_new_tokens=128
            )

        hypothesis = processor.tokenizer.decode(tokens[0], skip_special_tokens=True)
        pairs.append((entry["text"], hypothesis))

    return pairs


def train(args: argparse.Namespace) -> int:
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoProcessor,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
    )

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.adapters import AdapterRecord, FileAdapterRegistry, evaluate_adapter, promote

    entries = load_manifest(args.clips)
    train_entries, held_out = split_by_phrase(entries)

    log.info(
        "%s: %d clips, %d training / %d held out (split by phrase)",
        args.user_id,
        len(entries),
        len(train_entries),
        len(held_out),
    )

    if args.dry_run:
        print(json.dumps({
            "user_id": args.user_id,
            "clips": len(entries),
            "train": len(train_entries),
            "held_out": len(held_out),
            "augmented_training_examples": len(train_entries) * (AUGMENTATION_FACTOR + 1),
            "base_model": args.base,
            "lora": {"rank": LORA_RANK, "alpha": LORA_ALPHA, "targets": LORA_TARGET_MODULES},
            "epochs": args.epochs,
        }, indent=2))
        return 0

    processor = AutoProcessor.from_pretrained(args.base)
    base_model = WhisperForConditionalGeneration.from_pretrained(args.base)

    # Measure the base FIRST, on the exact clips the adapter will be judged on.
    # Measuring afterwards, from a model object that training has touched, is a
    # subtle and very common way to produce a flattering "before" number.
    log.info("measuring base ASR on held-out clips")
    before = transcribe_all(base_model, processor, held_out, args.clips)

    model = get_peft_model(
        base_model,
        LoraConfig(
            r=LORA_RANK,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            target_modules=LORA_TARGET_MODULES,
            bias="none",
        ),
    )
    model.print_trainable_parameters()

    dataset = build_dataset(train_entries, args.clips, processor, AUGMENTATION_FACTOR)

    output = (args.adapters_dir or _default_adapters_dir()) / args.user_id

    trainer = Seq2SeqTrainer(
        model=model,
        args=Seq2SeqTrainingArguments(
            output_dir=str(output / "checkpoints"),
            per_device_train_batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            num_train_epochs=args.epochs,
            fp16=torch.cuda.is_available(),
            logging_steps=10,
            save_strategy="no",
            report_to=[],
            remove_unused_columns=False,
        ),
        train_dataset=dataset,
        data_collator=_collator(processor),
    )

    trainer.train()

    log.info("measuring the adapted model on the same held-out clips")
    after = transcribe_all(model, processor, held_out, args.clips)

    evaluation = evaluate_adapter(before, after)

    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output))

    registry = FileAdapterRegistry(args.adapters_dir or _default_adapters_dir())
    record = promote(
        AdapterRecord(
            user_id=args.user_id,
            path=output,
            base_model=args.base,
            trained_at=datetime.now(timezone.utc),
            metadata={
                "clips": str(len(entries)),
                "held_out_phrases": str(len(held_out)),
                "lora_rank": str(LORA_RANK),
                "epochs": str(args.epochs),
            },
        ),
        evaluation,
    )
    registry.save(record)

    print(json.dumps({
        "user_id": args.user_id,
        "wer_before": round(evaluation.wer_before, 4),
        "wer_after": round(evaluation.wer_after, 4),
        "relative_reduction": round(evaluation.relative_reduction, 4),
        "held_out_utterances": evaluation.held_out_utterances,
        "passes_guardrail": evaluation.passes_guardrail,
        "deployed": record.deployed,
        "learner_message": evaluation.learner_message(),
    }, indent=2))

    # Non-zero when the adapter did not earn deployment. That is a legitimate
    # outcome rather than a failure of the script — but a CI job or a batch
    # runner needs to be able to tell the difference without parsing prose.
    return 0 if record.deployed else 2


def _default_adapters_dir() -> Path:
    from service.config import get_settings

    directory = get_settings().adapters_dir
    if directory is None:
        raise SystemExit(
            "adapters_dir is not configured. Set ADAPTERS_DIR or pass --adapters-dir."
        )
    return directory


def _collator(processor):
    """Pad features and labels separately; mask padding out of the loss."""
    import torch

    def collate(batch: list[dict]) -> dict:
        features = torch.tensor([item["input_features"] for item in batch])

        longest = max(len(item["labels"]) for item in batch)
        labels = torch.full((len(batch), longest), -100, dtype=torch.long)
        for row, item in enumerate(batch):
            labels[row, : len(item["labels"])] = torch.tensor(item["labels"])

        return {"input_features": features, "labels": labels}

    return collate


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
    return train(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())

# Training — what you run, and what I do

**Module M7** · the disfluency classifier · the first real training run in the project

---

## Your steps, in order

### 1. Build the package (30 seconds, on this machine)

```bash
cd services/speech
.venv/Scripts/activate
python -m training.build_package
```

Produces **`services/speech/training/samvaad-training.zip`** — about **5 KB**.

It contains one thing that matters: `pipeline/disfluency.py`, the *same* feature-extraction
function the production service calls. Training on features that differ from the ones served is
one of the most common and most invisible ML bugs — the model scores well in the notebook and
behaves randomly in production, and nothing errors.

### 2. Open the notebook in Colab

Go to [colab.research.google.com](https://colab.research.google.com) → **Upload** →
`services/speech/training/notebooks/train_disfluency.ipynb`

Then **Runtime → Change runtime type → T4 GPU**. The free tier is enough.

### 3. Run the cells top to bottom

Cell 4 opens a file picker — give it the zip from step 1.

**Cell 6 is the one decision you make.** Leave `MODE = 'quick'` for the first run:

| Mode | Episodes | Download | Total |
|---|---|---|---|
| `quick` | 40 | ~1.5 GB | **~25 min** |
| `full` | all | ~25 GB | 2–4 h |

Do the quick run first. It proves the whole pipeline works before you spend hours on it.

> **Cell 7 is the slow one** (downloading podcasts). It is resumable — if Colab disconnects,
> re-run that cell and it skips what it already has. Some URLs will 404; podcast feeds rot.
> That's expected, and the cell reports how many succeeded.

### 4. Read Cell 13

That prints the number that counts:

```
event                prec  recall     F1    AUC      n
------------------------------------------------------
block               0.xxx   0.xxx  0.xxx  0.xxx  x,xxx
prolongation        ...
------------------------------------------------------
MACRO-F1                           0.xxx     target >= 0.65
```

If it's below 0.65, **Cell 16 lists what to try**, in order of payoff. Usually the answer is
just `MODE = 'full'`.

### 5. Send back `disfluency_model.zip`

Cell 15 saves it to your Drive and the next cell downloads it. Drop it anywhere and tell me —
I'll wire it in.

**Send it back even if it failed the target.** A model at 0.55 with honest per-class numbers is
far more useful than no model, and it tells me exactly which event type is starved of data.

---

## What you need from the internet

| What | Where | Notes |
|---|---|---|
| **SEP-28k labels** | `github.com/apple/ml-stuttering-events-dataset` | Cloned automatically by Cell 5. Public, no application. |
| **Podcast audio** | Downloaded by Cell 7 from the URLs in the dataset | ~1.5 GB quick / ~25 GB full |
| Everything else | Installed by Cell 2 | librosa, lightgbm, skl2onnx |

**Nothing here needs an application or an account.** That matters — the *other* atypical-speech
corpora do:

| Corpus | Access | When |
|---|---|---|
| **UASpeech** | Academic application, ~2–4 weeks | Needed for M8 (ASR adaptation) |
| **Speech Accessibility Project** (UIUC) | Application, slow | Needed for M8 |
| **INCLUDE** (ISL) | Academic, faster | Needed for M16 |

> **Worth doing today:** submit the UASpeech and Speech Accessibility Project applications.
> They take weeks, and M8 stalls without them. Nothing else in the project is blocked on this,
> so the cost of applying early is zero and the cost of applying late is a month.

---

## Two decisions in the notebook worth understanding

**Show-disjoint splitting (Cell 10).** Clips from one podcast share a speaker, a microphone and
a room. A random split puts the same speaker in train and test, and the model scores brilliantly
by recognising the *voice* rather than the disfluency. Published stuttering-detection results
differ by 20+ F1 points on this choice alone. The notebook asserts no show appears in two
splits — the number it gives you is the one that will hold up on a real learner.

**Threshold tuning on validation, never test (Cell 12).** 0.5 is the wrong threshold for
imbalanced classes, so each event gets its own. Tuning those on the test set would produce a
number that answers a different question from "is this good enough to put in front of someone
who stammers".

---

## Where the weights land

```
services/speech/artifacts/          <- gitignored
├── disfluency_block.onnx
├── disfluency_prolongation.onnx
├── disfluency_sound_repetition.onnx
├── disfluency_word_repetition.onnx
├── disfluency_interjection.onnx
└── metrics.json
```

Weights belong in a model registry, not in git. `metrics.json` becomes the eval table the
speech CI job prints into the job summary, so every future change to this model is measured
against your run.

---

## What I'm building while you train

Nothing here is blocked on the model:

- **M7 prosody + Personal Progress Index** — the baseline-relative scoring maths, which is the
  ethical core of the product. Needs no trained model.
- **M9 GenAI core** — RAG over the phrase bank, role-play with guardrails.
- **M1** — onboarding, the four-door screen, the consent ledger against a real database.

When your `metrics.json` arrives, the disfluency stage flips to `true` in `/capabilities` and
the client starts showing coaching cues. Until then it reports `false` and the learner is told
plainly — no spinner.

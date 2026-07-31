# SAMVAAD

**An Ability-Adaptive Multimodal AI Coach for Workplace Communication & Employability**

A workplace-communication trainer for persons with disabilities, built on two ideas:

1. **Accessibility is architecture.** Every lesson is stored as modality-neutral data and rendered at runtime through whatever channels the learner can actually use — speech, text, Indian Sign Language, picture symbols, or Easy-Read. It is structurally impossible to ship a lesson that excludes someone.
2. **Scoring is baseline-relative.** Learners are measured against their own rolling baseline, never against a non-disabled reference speaker. The mock-interview rubric is architecturally blind to speech rate, articulation, gaze and affect — a fairness property proven by an automated test in CI, not merely claimed.

> *SAMVAAD* = Sanskrit for "dialogue".
> **S**upportive **A**ccessible **M**ultimodal **V**irtual **A**ssistant for **A**daptive **D**ialogue.

---

## Repository map

Everything is organised **module by module**, matching the module IDs (`M0`–`M19`) in
[`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md). Every directory has its own `README.md`
explaining what lives there and why.

```
samvaad/
├── packages/
│   ├── contracts/     ★ M0  The two data contracts everything depends on
│   └── content/         M3  The Workplace Language Bank (226 phrases) as source data
├── apps/
│   ├── web/             M2  React PWA — learner app, trainer & institution dashboards
│   └── api/             M1  FastAPI gateway — auth, CAP, content, sessions, consent
├── services/
│   ├── speech/        ★ M6  ASR · alignment · GOP · prosody · disfluency · PPI
│   └── genai/           M9  RAG · role-play · social stories · bias-guarded rubric
├── docs/                    Plan, ethics charter, ADRs, accessibility criteria
└── infra/                   Dockerfiles, deploy workflows, database migrations
```

`★` marks the two modules that carry the whole architecture. Read their READMEs first.

---

## Quick start

**Prerequisites:** Node ≥ 20, Python ≥ 3.10, Git.

```bash
git clone <this-repo> samvaad && cd samvaad

# 1 — contracts (build these first; both other stacks generate from them)
npm install
npm run contracts:build

# 2 — API gateway            → http://localhost:8000/healthz
cd apps/api      && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt && uvicorn app.main:app --reload

# 3 — speech service         → http://localhost:8100/healthz
cd services/speech && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt && uvicorn service.main:app --reload --port 8100

# 4 — web client             → http://localhost:5173
npm run dev:web
```

On macOS/Linux use `source .venv/bin/activate` instead of `.venv/Scripts/activate`.

---

## The two contracts

Everything in this codebase is built on two schemas in [`packages/contracts`](packages/contracts).
Understand these and the rest of the system follows.

| Contract | What it is | Why it matters |
|---|---|---|
| **`ContentBlock`** | A piece of learning content with a canonical meaning and a bundle of representations (audio, ISL clip, pictographs, Easy-Read, phonemes) — but **no chosen rendering** | The Modality Router picks the rendering at runtime from the learner's profile. Content authors never decide how something looks, so no module can ship inaccessible. |
| **`LearnerResponse`** | A learner's answer, normalised to a comparable `canonical_text` regardless of whether they spoke, typed, signed, or tapped symbols | One scoring engine, one recommender, one dashboard serve every disability profile. This removes ~60% of the work you'd otherwise duplicate per modality. |

JSON Schema is the single source of truth. TypeScript types and Pydantic models are
**generated** from it, and CI fails if the generated output drifts.

---

## Documentation

| Document | Read it when |
|---|---|
| [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md) | The full 24-week build plan, all 20 modules, architecture, ML inventory. **Start here.** |
| [`docs/ETHICS_CHARTER.md`](docs/ETHICS_CHARTER.md) | Before touching any scoring, feedback, or data-retention code. These rules are enforced by tests. |
| [`docs/ACCESSIBILITY.md`](docs/ACCESSIBILITY.md) | Before writing any UI. The acceptance criteria every screen must meet. |
| [`docs/PERSONAS.md`](docs/PERSONAS.md) | The five learners every feature is tested against. |
| [`docs/ADR/`](docs/ADR/) | Why the architecture is the way it is. Add one whenever you make a non-obvious call. |
| [`docs/source/`](docs/source/) | The original problem statement and submitted abstract. |

---

## Contributing rules

These are short because they are the ones that actually matter.

1. **Never import a renderer directly.** Feature code renders `<ModalityRouter>` / `<ModalityInput>`. An ESLint rule enforces this — it is what stops accessibility decaying over six months.
2. **Every PR states which persona(s) it was tested against.** See [`docs/PERSONAS.md`](docs/PERSONAS.md).
3. **Contract changes need approval from all tracks.** `packages/contracts` is load-bearing.
4. **ML changes ship with an eval table in the PR description.** No exceptions, no "it looked better".
5. **Write an ADR** for any decision a future reader would ask "why?" about.
6. **No time-pressure mechanics.** Ever. See Ethics rule E6.

---

## Licence

TBD before public release.

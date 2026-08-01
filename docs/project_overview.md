# SAMVAAD — Project Overview

> **SAMVAAD** = **S**upportive **A**ccessible **M**ultimodal **V**irtual **A**ssistant for **A**daptive **D**ialogue
> (*"Samvaad"* is Sanskrit for "dialogue")

---

## 🎯 The Problem Statement

**Persons with disabilities face a massive employability gap**, and a core bottleneck is **workplace communication skills** — knowing what to say in an interview, how to ask a supervisor for help, how to handle a customer. Existing communication trainers fail these users because:

1. **They assume a "standard" speaker.** ASR (speech recognition) word-error-rates on dysarthric speech can exceed 50%. Scoring systems penalise stammering, atypical speech, and slow response times. A person with cerebral palsy or a stammer is *scored down for having a disability*, not for lacking communication skill.

2. **They are single-modality.** A Deaf user who communicates in Indian Sign Language (ISL) is simply locked out. A user with intellectual disability who needs picture symbols (AAC) has no input path. "Accessible" usually means "added captions" — which doesn't help someone whose first language is ISL, not written English.

3. **They have no fairness guarantees.** Claims like "we don't discriminate" are unverified. No existing system can *prove* that a learner's stammer doesn't affect their interview score.

---

## 🏗️ What We Are Building

SAMVAAD is an **AI-powered workplace communication coach** that is *architecturally* accessible — not bolted-on-accessible. The system trains learners through drills, role-plays, and mock interviews, with two foundational design principles:

### Principle 1: Accessibility is Architecture

Every piece of learning content is stored as **modality-neutral data** (a `ContentBlock`). It has a canonical meaning plus bundles of representations — audio, ISL video clips, pictograph symbols, Easy-Read simplified text, phonemes — but **no chosen rendering**. At runtime, a **Modality Router** picks the right rendering based on the learner's profile. This makes it *structurally impossible* to ship a lesson that excludes someone.

### Principle 2: Scoring is Baseline-Relative

Learners are measured against **their own rolling baseline**, never against a non-disabled reference speaker. The mock-interview rubric is architecturally blind to speech rate, articulation, gaze, and affect. This is a **fairness property proven by automated tests in CI**, not merely claimed.

### The Five Personas Driving Design

Every feature is tested against five learners:

| Persona | Disability | Key Need |
|---|---|---|
| **P1 · Ravi** | Low vision (~10% residual) | Screen reader, no monitor needed |
| **P2 · Meena** | Profoundly Deaf (ISL) | Sign input/output, no audio |
| **P3 · Arjun** | Cerebral palsy (dysarthric speech) | Personalised ASR, switch scanning |
| **P4 · Fatima** | Intellectual disability (mild) | AAC symbols, Easy-Read, one idea per screen |
| **P5 · Karthik** | Moderate-severe stammer | No fluency scoring, no time pressure |

A feature that fails **any one** of them is not shippable.

---

## 🧱 Architecture & Repository Structure

The project is a **monorepo** with npm workspaces + Python services:

```
samvaad/
├── packages/
│   ├── contracts/     ★ M0   The two core data contracts (JSON Schema → TS + Pydantic)
│   ├── content/         M3   Workplace Language Bank (226 phrases)
│   └── platform/              Shared Python utilities (auth, redaction, logging)
├── apps/
│   ├── web/             M2   React PWA (Vite) — learner app + dashboards
│   └── api/             M1   FastAPI gateway — auth, CAP, content, sessions, consent
├── services/
│   ├── speech/        ★ M6   ASR · alignment · GOP · prosody · disfluency · PPI
│   └── genai/           M9   RAG · role-play · social stories · bias-guarded rubric
├── docs/                      Plan, ethics charter, personas, ADRs
└── infra/                     Dockerfiles, deploy workflows, DB migrations
```

### The Two Core Contracts

Everything is built on two schemas in [packages/contracts](file:///c:/Users/Welcome/Desktop/Workplace%20CT/packages/contracts):

| Contract | What it is | Why it matters |
|---|---|---|
| **`ContentBlock`** | Learning content with a canonical meaning + multiple representations (audio, ISL, pictographs, Easy-Read, phonemes) — but *no chosen rendering* | The Modality Router picks at runtime; content authors never decide how something looks |
| **`LearnerResponse`** | A learner's answer, normalised to a `canonical_text` regardless of input mode (speech, typing, sign, symbols) | One scoring engine + one recommender serves every disability profile |

---

## ✅ What Has Been Built So Far

### Completed Modules (9 of 20)

| Module | What it delivers |
|---|---|
| **M0 — Foundations** | Contracts, CI pipeline, ethics charter, 739 tests across 7 CI jobs |
| **M1 — Identity & Consent** | JWT auth, guest sessions, SQLAlchemy async DB, four-door onboarding, IDOR protection |
| **M2 — Modality Router** | Design system, runtime channel selection, `<ModalityRouter>` / `<ModalityInput>` components |
| **M3 — Language Bank** | 226 workplace phrases with phonemes, Easy-Read, pictograph mappings |
| **M4 — Practice Loop** | FSRS spaced-repetition engine, daily practice screen end-to-end |
| **M5 — Speech Capture** | Recording with consent, retention policies |
| **M6 — ASR & Scoring** | Whisper ASR, forced alignment, Goodness of Pronunciation (GOP) scoring |
| **M9 — GenAI Role-play** | RAG-powered role-play scenarios with guardrails, wired end-to-end |
| **M11 — Mock Interview** | Bias-guarded rubric with audit records, disfluency-invariant scoring |

### Partially Built (8 modules)

| Module | Done | Remaining |
|---|---|---|
| **M7 — Prosody/Disfluency** | Math + gates | Classifier weights not installed |
| **M8 — Personalised ASR** | Vocab biasing + enrolment | LoRA blocked on UASpeech dataset access |
| **M10 — Social Stories** | Service + gateway route | No client UI yet |
| **M14 — Dashboards** | Trainer dashboard with E5 enforcement | Learner + institution views not started |
| **M16 — ISL & AAC** | AAC input + ISL output | ISL recognition not started |
| **M17 — Privacy** | Consent, retention, redaction, erasure | No RLS, no data export |
| **M18 — Accessibility Validation** | axe + persona tests in CI | No manual screen-reader passes |
| **M19 — Observability** | Structured logging, tracing, redaction | No Sentry, no metrics dashboards |

### Not Started (3 modules)

- **M12** — Gamification
- **M13** — Recommendation engine
- **M15** — Offline-first & on-device inference

### Key Milestone

> **There are zero blocking gaps for a real learner.** A learner can open the app, be asked how they need to be communicated with, and have the answer shape everything that follows — persistently, under their own identity.

### CI & Testing

**739 tests** across 7 CI jobs — contracts, API (164 tests), speech (188 tests), genai (41 tests), platform (53 tests), web (173 tests), and an ethics job that verifies all 7 charter rules. Nothing merges without all seven green.

### Content Gaps

| Asset | Status |
|---|---|
| Phonemes | ✅ 226/226 done |
| Audio (native + slow) | 0/226 — needs TTS bootstrap |
| ISL clips | 3/226 — needs a Deaf signer |
| Pictograph verification | 0/226 human-checked |

---

## 📊 Summary

SAMVAAD is a **significant, well-architected project** that is already functional end-to-end for its core use case. The codebase is mature with strong testing, ethical guardrails enforced by CI, and a clear execution plan across 20 modules. The remaining work is *breadth* (more dashboards, gamification, offline support) and *depth* (ISL recognition, personalised ASR training data), not viability.

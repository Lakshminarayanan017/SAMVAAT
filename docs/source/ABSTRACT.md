# SMART ABILITY 2026 — Project Abstract

> **Fill before submission:** `Problem Statement ID`, `Team Name`, `Team Members`, `Mentor Name`, `Institution`.
> Everything else below is submission-ready. Slide-by-slide, matching the 4-slide reference template.

---

## SLIDE 1 — TITLE PAGE

| Field | Entry |
|---|---|
| **Problem Statement ID** | `<PS-ID from the SMART ABILITY 2026 portal>` |
| **Problem Statement Title** | AI-Assisted Workplace Communication Training Application for Persons with Disabilities |
| **Idea / Solution Title** | **SAMVAAD — An Ability-Adaptive Multimodal AI Coach for Workplace Communication & Employability** |
| **Theme** | Assistive Technology · Generative AI · Inclusive Skilling & Employability |
| **Team Name** | `<Team Name>` |
| **Team Members** | `<Member 1>`, `<Member 2>`, `<Member 3>`, `<Member 4>`, `<Member 5>`, `<Member 6>` |
| **Mentor Name** | `<Mentor Name>`, `<Designation, Department>` |
| **Institution** | `<College Name>` |

*(SAMVAAD = Sanskrit for "dialogue". Backronym: **S**upportive **A**ccessible **M**ultimodal **V**irtual **A**ssistant for **A**daptive **D**ialogue.)*

---

## SLIDE 2 — IDEA TITLE & PROPOSED SOLUTION

### Idea Title
**SAMVAAD — An Ability-Adaptive Multimodal AI Coach that trains, evaluates and certifies workplace communication for persons with disabilities.**

### One-line pitch
A single mobile + web application that **reshapes itself around each user's abilities** — speech, sign, text, symbol or audio — and uses Generative AI to rehearse real workplace conversations, measure progress **against the learner's own baseline instead of a "normal" speaker**, and hand employers a verifiable competency profile.

### Detailed explanation of the proposed solution

**1. Ability Profile & Modality Router (the core architectural idea).**
Onboarding builds a *Communication Ability Profile* — the user's usable **input** channels (voice / typing / sign / symbol-tap / switch) and **output** channels (audio / captions / Indian Sign Language / pictographs / haptics / Easy-Read). Every learning module is authored **once** as modality-neutral content and is rendered at runtime by a Modality Router. Accessibility is therefore *architecture*, not a bolt-on setting — the same mock interview runs as a spoken interview for a low-vision user, a captioned + ISL-avatar interview for a Deaf user, an AAC-symbol interview for a non-verbal user, and a one-step-per-screen Easy-Read interview for a user with intellectual disability.

**2. Curated Workplace Language Bank (200+ words & phrases).**
A structured corpus of 200+ workplace terms, phrases and functional expressions (greetings, self-introduction, asking for clarification, reporting progress, requesting leave/accommodation, disagreeing politely, handling feedback, telephone/e-mail etiquette, safety & compliance vocabulary). Each entry is tagged with: scenario, CEFR-style difficulty, phoneme profile, ISL sign clip, ARASAAC/Mulberry pictograph, native + slow-paced audio, and Easy-Read paraphrase. Delivery uses **spaced repetition (FSRS)** so revision is scheduled, not random.

**3. Disability-Aware Speech, Pronunciation & Fluency Engine.**
Off-the-shelf ASR and pronunciation scorers fail atypical speech and, worse, *penalise the disability itself*. SAMVAAD fixes both:
- **Personalised ASR** — a 30-phrase enrolment set adapts the recogniser per speaker (speaker-embedding conditioning + lightweight LoRA adaptation), so dysarthric, cleft-palate, deaf-speech and stammered speech are recognised reliably.
- **Baseline-relative scoring** — pronunciation is measured by Goodness-of-Pronunciation from forced-alignment posteriors, then normalised against **the user's own rolling baseline** to produce a *Personal Progress Index*. The learner competes with yesterday's self, never with a native speaker.
- **Fluency & prosody analytics** — speech rate, articulation rate, pause distribution, filler/repetition/prolongation/block detection, pitch & energy variation. Stammering events are surfaced as *coaching cues* (breath, easy-onset, pausing strategy), never as errors.

**4. Generative AI Scenario & Role-Play Engine.**
An LLM, grounded by RAG over the curated corpus + workplace-etiquette guidelines, drives live role-play with an AI recruiter, manager, teammate or client. Difficulty adapts in real time along a Zone-of-Proximal-Development curve. Every AI turn is schema-constrained and safety-filtered, so the conversation stays in-scenario, in-vocabulary and non-toxic.

**5. Auto-Generated Social Stories.**
Social stories in the standard descriptive/perspective/directive structure are generated for the learner's **actual** job context ("my first day at the packaging unit", "asking my supervisor to repeat an instruction") and rendered simultaneously as Easy-Read text + pictograph strip + narrated audio + ISL clip.

**6. Mock Interview & HR Interaction Simulator with a Bias-Guarded Rubric.**
Full HR/technical/telephonic interview simulation. Scoring evaluates **content, structure (STAR), relevance, clarity of intent and self-advocacy** — and the rubric explicitly *excludes* traits that are manifestations of disability (speech rate, articulation, gaze, facial affect, motor stillness). Optional, opt-in, fully **on-device** camera analysis gives gentle posture/eye-contact cues without any video ever leaving the phone. A "Disclosure & Accommodation Coach" rehearses the hardest real conversation of all: how and whether to ask an employer for a reasonable accommodation.

**7. Gamification, Personalisation & Dashboards.**
3–5 minute micro-lessons, streaks, XP, badges and achievement tiers tuned for sustained motivation. A recommendation layer selects the next activity from the learner's error signature, retention curve and confidence self-report. Three dashboards — **Learner** (progress, replays, personal bests), **Trainer/Special Educator** (cohort heatmap, per-skill drill-down, ability to override AI feedback and assign tasks), **Institution/Employer** (anonymised competency analytics, placement-readiness view, consent-gated).

**8. Works where the learners actually are.**
Offline-first: quantised on-device ASR/TTS via ONNX Runtime keeps practice working with no network; cloud LLM calls sync opportunistically. English + Tamil/Hindi with code-mixed handling. Runs on entry-level Android.

### How it addresses the problem

| Problem-statement requirement | How SAMVAAD delivers it |
|---|---|
| Barriers from non-inclusive training platforms | Modality Router: one app renders in speech / sign / symbol / audio / Easy-Read — WCAG 2.2 AA + IS 17802 targeted |
| 200 workplace words & phrases | 200+ entry Workplace Language Bank, multi-tagged, spaced-repetition scheduled |
| Speech, pronunciation, fluency analysis | Personalised ASR + GOP scoring + prosody/disfluency analytics, baseline-relative |
| AI-assisted contextual learning | RAG-grounded LLM tutor that teaches phrases *inside* the scenario that needs them |
| Social stories | Auto-generated, job-context specific, quad-modal rendering |
| Interactive workplace simulations | Live multi-turn role-play with adaptive difficulty and branching outcomes |
| Personalised recommendations | Error-signature + retention-curve driven next-best-activity engine |
| Mock interview & HR simulator | Full simulator with bias-guarded rubric + accommodation-disclosure coach |
| Gamified modules | Micro-lessons, XP, streaks, badges, achievement tiers |
| Dashboards for learners/trainers/institutions | Three role-based dashboards with consent-gated employer analytics |

### Innovation & uniqueness

1. **Baseline-relative assessment** — the first design decision that makes AI speech scoring *ethical* for PwDs. Existing pronunciation apps score against a neurotypical native reference, which guarantees a low score for a disabled learner regardless of effort. SAMVAAD scores the delta from the learner's own baseline.
2. **Accessibility as architecture, not as a settings screen** — content is authored once, modality-neutral; the router guarantees no module can ship inaccessible to any profile.
3. **Bias-guarded interview rubric** — an explicit, auditable exclusion list preventing the AI from penalising disability characteristics; directly counters the documented discrimination of AI hiring tools.
4. **Personalised ASR for atypical speech** — few-shot speaker adaptation, so the users most excluded by mainstream voice tech become first-class users.
5. **Accommodation-Disclosure Coach** — rehearses the conversation no existing communication trainer covers, and the one that most decides whether a PwD keeps a job.
6. **Human-in-the-loop by design** — AI is a co-pilot to the special educator/speech therapist, who can review, override and assign. Trust, not replacement.
7. **Offline-first on entry-level Android** — the special schools, NGOs and NIEPMD-affiliated centres that need this most are exactly where bandwidth is not.

---

## SLIDE 3 — TECHNICAL APPROACH

### Technologies to be used

**Frontend / Client**
- **Flutter** (Android · iOS · Web) — single codebase, first-class `Semantics` tree for TalkBack/VoiceOver
- **React + TypeScript + Tailwind** — trainer & institution web dashboards
- **Accessibility layer** — WCAG 2.2 AA, IS 17802, dynamic type, high-contrast & dark themes, switch-access & keyboard-only navigation, `axe-core` in CI

**Backend / Platform**
- **FastAPI (Python)** microservices · **Node.js** gateway · **Celery + Redis** async jobs
- **PostgreSQL + pgvector** (relational + embeddings) · **MinIO/S3** (audio artefacts) · **Docker + Kubernetes** · **GitHub Actions** CI/CD

**Speech & Audio AI**
- **Whisper large-v3** (cloud) + **distil-Whisper / Whisper-small INT8 via ONNX Runtime** (on-device)
- **wav2vec 2.0 / WavLM** phoneme posteriors → **Goodness-of-Pronunciation** scoring
- **Montreal Forced Aligner** — phoneme-level alignment
- **openSMILE · Praat/Parselmouth · librosa** — prosody, pause & disfluency features
- **SpeechBrain** — speaker embeddings & personalised adaptation (LoRA)
- **Piper / Coqui TTS** — expressive, on-device, adjustable-rate speech output

**Generative AI / NLP**
- **Claude (Anthropic API)** for scenario generation, coaching feedback & social stories; **Llama-3.1-8B-Instruct** fine-tuned via QLoRA as the self-hostable fallback
- **RAG** — `sentence-transformers` embeddings over the Workplace Language Bank + etiquette corpus, stored in pgvector
- **Guardrails** — JSON-schema-constrained outputs, rubric-locked scoring prompts, toxicity & scope filters, cited-source grounding

**Assistive & Multimodal**
- **MediaPipe Holistic** — ISL gesture recognition (input) and on-device gaze/posture cues (opt-in)
- **ISL avatar** — pre-recorded clip library + Three.js/Blender 3D signing avatar (output)
- **ARASAAC / Mulberry** CC-licensed symbol sets for the AAC board

**Data, Privacy & MLOps**
- **MLflow** experiment tracking · **ONNX Runtime** edge inference · **Grafana + Prometheus** telemetry
- **DPDP Act 2023** aligned — explicit consent, guardian mode, voice biometrics and video never leave the device, raw audio auto-purged after feature extraction, role-based access control, full data-export & erase

### Methodology and process for implementation

**Phase 1 · Co-Design & Requirements (Weeks 1–2)**
Participatory design workshops with PwD learners, special educators, speech-language pathologists and employers. Output: 5 persona-profiles, accessibility acceptance criteria, ethical scoring charter.

**Phase 2 · Content & Data Engineering (Weeks 2–4)**
Author the 200+ phrase bank; record native + slow audio; map ISL clips and pictographs; write Easy-Read paraphrases; build the scenario/social-story seed corpus; assemble an atypical-speech evaluation set for validation.

**Phase 3 · AI Core (Weeks 3–7)**
Build the speech pipeline (ASR → forced alignment → GOP → prosody/disfluency → Personal Progress Index); implement personalised speaker adaptation; build the RAG + role-play engine with guardrails; implement the bias-guarded rubric and its audit log.

**Phase 4 · Application Build (Weeks 4–9)**
Flutter client with the Modality Router; scenario player; mock-interview simulator; gamification & spaced-repetition scheduler; three role-based dashboards; offline sync layer.

**Phase 5 · Accessibility Validation & Pilot (Weeks 9–12)**
Automated (`axe-core`) + manual screen-reader and switch-access audits; pilot with a PwD learner cohort; pre/post measurement of the Personal Progress Index, mock-interview rubric scores and self-reported confidence; trainer feedback loop.

**Phase 6 · Iterate, Harden & Scale (Continuous)**
Model refresh from consented data, multilingual expansion, employer-portal integration, deployment playbook for special schools and NGOs.

### System architecture (flow)

```
                    ┌──────────────────────────────────────────────┐
                    │  ONBOARDING → Communication Ability Profile   │
                    │  (input channels · output channels · goals)   │
                    └──────────────────────┬───────────────────────┘
                                           ▼
        ┌──────────────────────── MODALITY ROUTER ────────────────────────┐
        │  Speech  │  Text  │  Indian Sign Language  │  AAC Symbols  │ Easy-Read │
        └────┬──────────┬───────────┬────────────┬────────────┬───────────┘
             ▼          ▼           ▼            ▼            ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │                      LEARNING & PRACTICE LAYER                     │
   │  Phrase Bank (200+) · Social Stories · Scenario Role-Play ·        │
   │  Mock Interview & HR Simulator · Gamified Micro-Lessons            │
   └──────────────┬───────────────────────────────┬────────────────────┘
                  ▼                               ▼
   ┌──────────────────────────────┐  ┌────────────────────────────────┐
   │   SPEECH & LANGUAGE ENGINE   │  │   GENERATIVE AI ENGINE (RAG)    │
   │  Personalised ASR            │  │  Scenario generation            │
   │  Forced alignment → GOP      │  │  Adaptive difficulty (ZPD)      │
   │  Prosody · pause · disfluency│  │  Social-story authoring         │
   │  → Personal Progress Index   │  │  Coaching feedback (guardrailed)│
   └──────────────┬───────────────┘  └────────────────┬───────────────┘
                  └───────────────┬───────────────────┘
                                  ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │  ADAPTIVE FEEDBACK + RECOMMENDATION ENGINE                         │
   │  error signature · retention curve · confidence · bias-guarded rubric│
   └──────────────┬────────────────────────────────────────────────────┘
                  ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │  DASHBOARDS   Learner  │  Trainer / Educator  │ Institution & Employer│
   └───────────────────────────────────────────────────────────────────┘
        Cross-cutting: Offline-first cache · On-device inference ·
        Consent & DPDP-2023 privacy vault · Human-in-the-loop override
```

---

## SLIDE 4 — IMPACT AND BENEFITS

### Potential impact on the target audience
- **Scale of need** — India has **2.68 crore persons with disabilities** (Census 2011, ~2.21% of the population) and the RPwD Act 2016 recognises **21 disability types** with a **4% reservation** in government employment; globally the WHO estimates **1.3 billion people (16%)** live with significant disability. Workforce participation remains far below the national average, and communication confidence is repeatedly cited as a decisive barrier at the interview stage.
- **Removes the gatekeeper barrier** — candidates who are technically qualified but fail at the interview conversation get unlimited, judgement-free, private rehearsal.
- **First-class access for the most excluded** — non-verbal, Deaf, low-vision and intellectually disabled learners get the *same* curriculum, not a reduced one.
- **Multiplies scarce specialists** — one special educator or speech therapist can supervise a far larger cohort, because routine drill and measurement are automated and reviewable.
- **Dignity by design** — measuring progress against the learner's own baseline replaces a lifetime of being scored against a norm they were never going to meet.

### Benefits of the solution

**Social**
- Higher employability, retention and workplace independence for PwDs; reduced isolation through rehearsed social participation.
- Directly advances **UN SDG 4 (Inclusive Education), SDG 8 (Decent Work), SDG 10 (Reduced Inequalities)** and the **UNCRPD** right to work.
- Shifts the burden of adaptation partly onto tooling instead of entirely onto the disabled person.

**Economic**
- Raises earning capacity and reduces dependency for PwD households.
- Cuts employer onboarding and communication-support cost; strengthens **RPwD Act 2016** and **CSR/DEI** compliance with evidence.
- Marginal cost per additional learner approaches zero — the whole point of an AI tutor over 1:1 coaching hours.

**Institutional & Systemic**
- Special schools, NGOs, NIEPMD centres, NSDC/skilling partners and placement cells gain objective, longitudinal competency analytics instead of subjective impressions.
- The consented, de-identified atypical-speech corpus becomes a public good — the single biggest bottleneck in inclusive speech AI for Indian languages today.

**Technological / Environmental**
- Offline-first, on-device inference on entry-level Android → reaches rural and low-bandwidth institutions and cuts inference energy and cloud cost.
- Modality Router and the bias-guarded rubric are reusable patterns for any downstream inclusive-AI product.

### Success metrics for the pilot
| Metric | Target |
|---|---|
| Personal Progress Index (pronunciation/fluency) | ≥ 25% improvement over a 12-week pilot |
| Mock-interview rubric score | ≥ 30% improvement, pre vs. post |
| Self-reported interview confidence (1–5) | ≥ +1.5 points |
| Workplace phrase retention @ 30 days | ≥ 80% |
| Weekly active learner retention | ≥ 60% at week 8 |
| Accessibility conformance | WCAG 2.2 AA — zero critical `axe` violations; screen-reader & switch-access verified |
| Trainer agreement with AI feedback | ≥ 85% acceptance without override |

---

## Compact abstract (150–200 words) — for a plain-text registration field

> **SAMVAAD** is an ability-adaptive, multimodal AI coach that trains, evaluates and certifies workplace communication skills for persons with disabilities. Onboarding builds a Communication Ability Profile, and a Modality Router renders every lesson through the learner's usable channels — speech, text, Indian Sign Language, AAC symbols or Easy-Read — so accessibility is architectural rather than an afterthought. A curated bank of 200+ workplace words and phrases is delivered through spaced repetition, generative-AI role-play with an AI recruiter, manager or teammate, auto-generated social stories, and a full mock-interview and HR-interaction simulator. A disability-aware speech engine combines personalised ASR for atypical speech with Goodness-of-Pronunciation and prosody analysis, scoring each learner **against their own rolling baseline** instead of a neurotypical reference, while a bias-guarded interview rubric explicitly refuses to penalise traits that are manifestations of disability. Gamified micro-lessons sustain motivation; learner, trainer and institution dashboards make competency measurable. The system is offline-first with on-device inference, human-in-the-loop reviewable, and DPDP-2023 compliant.

---

## Pre-submission checklist
- [ ] Problem Statement ID filled from the portal
- [ ] Team name, all member names, mentor name & institution filled on Slide 1
- [ ] Slide 3 architecture converted to a clean flowchart graphic (the ASCII block above is the blueprint)
- [ ] Deck exported to the format the portal demands (usually PDF)
- [ ] File named per the portal convention (commonly `PS-ID_TeamName.pdf`)
- [ ] Page/slide count within the stated limit

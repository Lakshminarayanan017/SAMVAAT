# Status & Gap Register

**Updated:** 2026-08-01 · Update this file in the same commit as the work it describes.

A module is only "done" when a learner can reach it. Code that passes its tests but is
unreachable from the client is **built, not done** — that distinction is the whole point of this
page, and it is how M9–M11 sat finished-and-invisible for a day.

---

## Modules

| # | Module | State | Note |
|---|---|---|---|
| M0 | Foundations, contracts, CI, ethics charter | ✅ done | |
| M1 | Identity, consent & CAP | 🟡 partial | CAP contract + provider + consent ledger exist. **No auth, no onboarding funnel, no database.** |
| M2 | Modality Router & design system | ✅ done | |
| M3 | Workplace Language Bank | ✅ done | 226 phrases. Assets outstanding — see below. |
| M4 | Practice loop (FSRS) | ✅ done | Reachable end-to-end. |
| M5 | Speech capture, consent, retention | ✅ done | |
| M6 | ASR, alignment, GOP | ✅ done | Needs `requirements-ml.txt` installed to activate. |
| M7 | Prosody, disfluency, PPI | 🟡 partial | Maths + gates done. **Classifier weights not yet dropped in.** |
| M8 | Personalised ASR adaptation | 🟡 partial | Vocabulary biasing + enrolment done. **LoRA blocked on UASpeech access.** |
| M9 | GenAI role-play (RAG, guardrails) | ✅ done | Wired to gateway and client. |
| M10 | Social stories | 🟡 partial | Service + gateway route exist. **No client UI.** |
| M11 | Mock interview & bias-guarded rubric | ✅ done | Wired end-to-end; audit record persisted. |
| M12 | Gamification | ⬜ not started | |
| M13 | Recommendation engine | ⬜ not started | Session builder does a simple version already. |
| M14 | The three dashboards | ⬜ not started | Blocks Ethics E5 enforcement. |
| M15 | Offline-first & on-device inference | ⬜ not started | |
| M16 | ISL & AAC depth | 🟡 partial | AAC input + ISL output done. **ISL recognition not started** — blocks E4. |
| M17 | Privacy hardening | 🟡 partial | Consent + retention + redaction + service auth done. **No database, no RLS, no export/erasure UI.** |
| M18 | Accessibility validation & pilot | 🟡 partial | axe + persona tests in CI. **No manual screen-reader passes. No pilot partner.** |
| M19 | Observability & MLOps | 🟡 partial | Structured logging, tracing, redaction shipped. **No Sentry, no metrics, no dashboards.** |

**8 done · 8 partial · 4 not started.**

---

## Gaps, ranked by what they block

### 🔴 Blocking a real learner

| Gap | Consequence | Where |
|---|---|---|
| **No database.** Every store is in-memory behind a Protocol | Restart the API and every learner loses their cards, conversations, consents and audit records | M1 |
| **No authentication.** `user_id` is supplied by the caller | Anyone can read anyone's interview by guessing a user id | M1 |
| **No onboarding.** The CAP is hard-coded to a demo persona | A real learner cannot tell us how they need to be spoken to | M1 |

Everything else is comfort. These three are why this is a demo and not a product.

### 🟠 Blocking a claim we make

| Gap | Claim it undermines | Where |
|---|---|---|
| **E4 has no enforcing test** | "Video never leaves the device" is currently a promise, not a proof | M16 |
| **E5 has no enforcing test** | "Every AI score is human-overridable" — there is no trainer surface at all | M14 |
| **No manual screen-reader passes** | axe catches ~30%. NVDA/VoiceOver/TalkBack have never been run against this | M18 |
| **Disfluency weights not installed** | Coaching cues cannot appear; `/capabilities` correctly reports `false` | M7 |

### 🟡 Content and data debt

| Gap | Status | Needs |
|---|---|---|
| **Audio** (native + slow) | 0 / 226 | TTS bootstrap; manifest ready in `content/dist/index.json` |
| **ISL clips** | 3 / 226 | A Deaf signer or ISL interpreter. **Start outreach — this has a long lead time.** |
| **Pictograph verification** | 0 / 226 human-checked | Automatic mapping produces embarrassing results |
| **UASpeech / Speech Accessibility Project** | not applied for | 2–4 week turnaround. **M8 stalls without it.** |
| Phonemes | ✅ 226 / 226 | done |

### ⚪ Known and accepted, for now

| Thing | Why it is acceptable today | When it stops being |
|---|---|---|
| Content bundled into the JS (~80 kB gzipped) | Fine for a demo | Before the pilot — M15 moves it to IndexedDB |
| No client-side router | Two views do not justify one | M14, when dashboards arrive |
| Free tiers sleep on idle (~30 s cold start) | Tolerable in development | Before the pilot; fix is a paid dyno, not a rewrite |
| `packages/platform` needs pip ≥ 21.3 | Editable install needs PEP 660 | Document it; it produces a confusing error otherwise |
| Social stories have no UI | The endpoint works and is testable | Whenever a learner is meant to read one |

---

## What CI actually gates

| Job | Covers |
|---|---|
| `contracts` | Schema, drift, accessibility rules, gate self-test, 226 phrases |
| `api` | 108 tests, lint, cross-language contract round-trip |
| `speech` | 188 tests, lint, PPI monotonicity + disfluency-invariance fairness gates |
| `genai` | 41 tests, lint, `TestDisfluencyInvariance` |
| `platform` | 53 tests, lint, redaction policy + fail-closed service auth |
| `web` | 126 tests, lint, typecheck, build, axe sweep across every channel and input mode |
| `ethics` | All 7 charter rules present; **every path the charter cites exists** |

**638 tests.** Nothing merges without all seven green.

---

## Rules that keep this file honest

1. **Update it in the same commit as the work.** A status page updated separately is a status page nobody trusts.
2. **"Done" means a learner can reach it.** Not "the tests pass".
3. **A gap with no owner and no trigger is a wish.** Every 🔴 and 🟠 row names the module that closes it.
4. **Do not delete a gap because it is embarrassing.** The three 🔴 rows above are the most useful lines on this page.

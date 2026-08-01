# Status & Gap Register

**Updated:** 2026-08-01 (M15 offline-first) · Update this file in the same commit as the work it describes.

A module is only "done" when a learner can reach it. Code that passes its tests but is
unreachable from the client is **built, not done** — that distinction is the whole point of this
page, and it is how M9–M11 sat finished-and-invisible for a day.

---

## Modules

| # | Module | State | Note |
|---|---|---|---|
| M0 | Foundations, contracts, CI, ethics charter | ✅ done | |
| M1 | Identity, consent & CAP | ✅ done | Auth, guest sessions, database, repositories, four-door onboarding. Speech enrolment (stage 3) deferred to M8 by design. |
| M2 | Modality Router & design system | ✅ done | |
| M3 | Workplace Language Bank | ✅ done | 226 phrases. Assets outstanding — see below. |
| M4 | Practice loop (FSRS) | ✅ done | Client screen shipped; reachable end-to-end. |
| M5 | Speech capture, consent, retention | ✅ done | |
| M6 | ASR, alignment, GOP | ✅ done | Needs `requirements-ml.txt` installed to activate. |
| M7 | Prosody, disfluency, PPI | 🟡 partial | Maths + gates done. **Classifier weights not yet dropped in.** |
| M8 | Personalised ASR adaptation | 🟡 partial | Vocabulary biasing + enrolment done. **LoRA blocked on UASpeech access.** |
| M9 | GenAI role-play (RAG, guardrails) | ✅ done | Wired to gateway and client. |
| M10 | Social stories | 🟡 partial | Service + gateway route exist. **No client UI.** |
| M11 | Mock interview & bias-guarded rubric | ✅ done | Wired end-to-end; audit record persisted. |
| M12 | Gamification | ✅ done | XP for effort, non-punishing streaks, courage/growth badges. |
| M13 | Recommendation engine | ✅ done | Rule-based and explainable. Every suggestion carries a reason the learner can read. Contextual bandit stays `[V2]`. |
| M14 | The three dashboards | 🟡 partial | Trainer and learner views done. **Institution view not started** (needs the k-anonymity floor). |
| M15 | Offline-first & on-device inference | 🟡 partial | Service worker, IndexedDB, append-only outbox, content un-bundled. **On-device ASR not started.** |
| M16 | ISL & AAC depth | 🟡 partial | AAC input + ISL output done. **ISL recognition not started** — blocks E4. |
| M17 | Privacy hardening | 🟡 partial | Consent, retention, redaction, service auth, self-service erasure done. **No RLS, no data export.** |
| M18 | Accessibility validation & pilot | 🟡 partial | axe + persona tests in CI. **No manual screen-reader passes. No pilot partner.** |
| M19 | Observability & MLOps | 🟡 partial | Structured logging, tracing, redaction shipped. **No Sentry, no metrics, no dashboards.** |

**11 done · 7 partial · 1 not started.**

---

## Gaps, ranked by what they block

### 🔴 Blocking a real learner

**None.** For the first time, a learner can open this, be asked how they need to
be spoken to, and have the answer shape everything that follows — persistently,
under their own identity.

**Closed since the last update:**

| Was | Now |
|---|---|
| ~~No database~~ | SQLAlchemy async, SQLite in dev and tests, Postgres in production. |
| ~~No authentication~~ | JWT sessions, guest-first. `user_id` **removed from every request model**. IDOR regression suite. |
| ~~No onboarding~~ | Four-door screen, then confirmation asked *through* the chosen channel. |
| ~~E5 not enforced~~ | Trainer dashboard. Overrides written **onto** the audit record, never over the AI's score, with a required reason. `TestEthicsE5`. |
| ~~Practice loop had no client screen~~ | Shipped. The daily loop a learner actually opens. |

**Six of seven charter rules are now enforced by a test.** Only E4 remains,
and it cannot be written until camera code exists (M16).

What remains is breadth, not viability.

### 🟠 Blocking a claim we make

| Gap | Claim it undermines | Where |
|---|---|---|
| **E4 has no enforcing test** | "Video never leaves the device" is currently a promise, not a proof | M16 |
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
| No client-side router | Two views do not justify one | M14, when dashboards arrive |
| Free tiers sleep on idle (~30 s cold start) | Tolerable in development | Before the pilot; fix is a paid dyno, not a rewrite |
| `packages/platform` needs pip ≥ 21.3 | Editable install needs PEP 660 | Document it; it produces a confusing error otherwise |
| No password or magic-link sign-in | Guest + upgrade covers the demo, and passwords are a liability we do not need | M17, when Supabase Auth lands behind the same `authenticate` dependency |
| No Alembic migrations yet | `create_all` is correct for SQLite dev and tests | First Postgres deployment — `create_all` cannot alter a table and fails silently |
| Social stories have no UI | The endpoint works and is testable | Whenever a learner is meant to read one |
| The recommender cannot see weak phonemes yet | GOP is not live, and inventing a weakness would be worse than omitting one — the other signals simply carry more weight | When M6's GOP lands |
| Institution dashboard not built | Needs the k-anonymity floor (suppress cells below n=5) designed first, and no institution is using this yet | M14 remainder |
| On-device ASR not wired | The offline shell, cache and outbox all work without it; a learner practises offline by typing or tapping symbols and speech analysis queues for reconnect | M15 remainder — needs `onnxruntime-web` and a quantised Whisper |
| PWA manifest has no icons | Installability works; the icon set needs a designer, not a developer | Before the pilot |
| Session token in `localStorage` | An httpOnly cookie needs a same-site deployment we do not have, and would break offline identity in M15 | When client and API share a domain |

---

## What CI actually gates

| Job | Covers |
|---|---|
| `contracts` | Schema, drift, accessibility rules, gate self-test, 226 phrases |
| `api` | 216 tests, lint, cross-language round-trip, IDOR suite, `TestEthicsE5` |
| `speech` | 188 tests, lint, PPI monotonicity + disfluency-invariance fairness gates |
| `genai` | 41 tests, lint, `TestDisfluencyInvariance` |
| `platform` | 53 tests, lint, redaction policy + fail-closed service auth |
| `web` | 207 tests, lint, typecheck, build, axe sweep across every channel and input mode |
| `ethics` | All 7 charter rules present; **every path the charter cites exists** |

**825 tests.** Nothing merges without all seven green.

---

## Rules that keep this file honest

1. **Update it in the same commit as the work.** A status page updated separately is a status page nobody trusts.
2. **"Done" means a learner can reach it.** Not "the tests pass".
3. **A gap with no owner and no trigger is a wish.** Every 🔴 and 🟠 row names the module that closes it.
4. **Do not delete a gap because it is embarrassing.** The 🔴 rows are the most useful lines on this page.
5. **When a gap closes, move it into "Closed since the last update" rather than deleting it.** Knowing what was fixed and when is how the next person judges whether the rest of this page is trustworthy.

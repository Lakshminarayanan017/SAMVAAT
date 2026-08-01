# Status & Gap Register

**Updated:** 2026-08-01 (Redesign Blueprint Phase 1 — primitives, semantic tokens, router, flags) · Update this file in the same commit as the work it describes.

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
| M10 | Social stories | ✅ done | Reachable. Panels are converted to `ContentBlock`s and rendered through the Modality Router, so a generated story reaches a pictograph reader as symbols rather than prose. Situations are a fixed list, not free text — see the gap table. |
| M11 | Mock interview & bias-guarded rubric | ✅ done | Wired end-to-end; audit record persisted. |
| M12 | Gamification | ✅ done | XP for effort, non-punishing streaks, courage/growth badges. |
| M13 | Recommendation engine | ✅ done | Rule-based and explainable. Every suggestion carries a reason the learner can read. Contextual bandit stays `[V2]`. |
| M14 | The three dashboards | ✅ done | Learner, trainer and institution views all reachable. Cohort figures pass a k-anonymity floor (n=5) that also withholds any cell whose *complement* is small, so published figures cannot be subtracted to recover a hidden one. |
| M15 | Offline-first & on-device inference | 🟡 partial | Service worker, IndexedDB, append-only outbox, content un-bundled. **On-device ASR not started.** |
| M16 | ISL & AAC depth | 🟡 partial | AAC input + ISL output done. **ISL recognition not started** — blocks E4. |
| M17 | Privacy hardening | 🟡 partial | Consent, retention, redaction, service auth, export and erasure — all reachable from a "Your data" screen. **No RLS.** |
| M18 | Accessibility validation & pilot | 🟡 partial | axe + persona tests in CI. **No manual screen-reader passes. No pilot partner.** |
| M19 | Observability & MLOps | 🟡 partial | Structured logging, tracing, redaction shipped. **No Sentry, no metrics, no dashboards.** |

**13 done · 7 partial · 0 not started.** (20 modules, counted from the table above.)

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
| ~~No client-side router~~ | React Router, behind one `<AppRoute>` wrapper that moves focus, announces and sets the title on every navigation — with a test that walks the real route table so a route added without it fails CI. See [ADR-0008](ADR/0008-accessible-route-contract.md). |
| ~~No UI primitives~~ | `apps/web/src/ui/` — twelve primitives. Feature screens no longer invent their own button, spacing or idea of "muted text". |
| ~~No code splitting~~ | Route-level lazy imports. Entry chunk **69.8 KB gzipped** against a 120 KB budget, enforced by `npm run check:bundle`. |
| ~~No feature flags~~ | `packages/platform/samvaad_platform/flags.py`, served to the client at `/flags`. Every redesign phase ships behind one whose off-state is the current behaviour. |
| ~~Erasure left three tables behind~~ | **Found by writing the test that walks the schema instead of a list of tables.** `DELETE /auth/me` reported "everything about you has been deleted" while the communication profile, the consent ledger and the trainer link all survived — the user row is removed with a Core `delete()`, which does not run ORM cascades, and SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON`. The trainer link carries `display_name`: the learner's real name. Fixed, and the schema walk now fails on any table that still names an erased learner. |
| ~~No data export~~ | `GET /export/me`. Leads with a plain-language summary, then the complete record. Checked against the schema so it cannot drift from what erasure deletes. |
| ~~Export and erasure were API-only~~ | A "Your data" screen. Both rights were unreachable from the client, which made "self-service" a claim rather than a fact. |
| ~~Social stories unreachable~~ | Shipped. The last case of "built but invisible" — the endpoint had worked since M10 with nothing in the product able to open one. |
| ~~Institution dashboard not built~~ | Shipped, behind three gates. The one worth naming is the third: a cohort figure is withheld when the cell **or its complement** falls below n=5, and if a breakdown would leave exactly one category hidden, a second goes too — otherwise the published columns subtract to reveal it. In a centre of twelve, "1 learner uses Indian Sign Language" names that person to everyone who works there. |

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
| Free tiers sleep on idle (~30 s cold start) | Tolerable in development | Before the pilot; fix is a paid dyno, not a rewrite |
| `packages/platform` needs pip ≥ 21.3 | Editable install needs PEP 660 | Document it; it produces a confusing error otherwise |
| No password or magic-link sign-in | Guest + upgrade covers the demo, and passwords are a liability we do not need | M17, when Supabase Auth lands behind the same `authenticate` dependency |
| No Alembic migrations yet | `create_all` is correct for SQLite dev and tests | First Postgres deployment — `create_all` cannot alter a table and fails silently |
| Social stories cover six preset situations, not free text | A text box would shut out the two personas most likely to need a story — describing a confusing situation in writing is the skill they came here lacking — and would put learner-controlled text into a model prompt. The list is the accessible option *and* the safe one | When a trainer can author situations for their own caseload. That keeps the learner's input an index into a list, not prose |
| The recommender cannot see weak phonemes yet | GOP is not live, and inventing a weakness would be worse than omitting one — the other signals simply carry more weight | When M6's GOP lands |
| The cohort report has no date range | Deliberate. Every filter parameter is a way to narrow a cohort until one person is left, and a date range is the easiest one to abuse — "learners active in this one week" can be a group of one. A range is only safe with a query budget we do not have | When there is a real reporting need *and* a per-institution query budget to bound it |
| On-device ASR not wired | The offline shell, cache and outbox all work without it; a learner practises offline by typing or tapping symbols and speech analysis queues for reconnect | M15 remainder — needs `onnxruntime-web` and a quantised Whisper |
| PWA manifest has no icons | Installability works; the icon set needs a designer, not a developer | Before the pilot |
| Session token in `localStorage` | An httpOnly cookie needs a same-site deployment we do not have, and would break offline identity in M15 | When client and API share a domain |

---

## What CI actually gates

| Job | Covers |
|---|---|
| `bundle` | Entry chunk <=120 KB gzipped (currently 69.8 KB), no route chunk over 60 KB |
| `contracts` | 20 checks — schema, drift, accessibility rules, gate self-test, 226 phrases |
| `api` | 299 tests, lint, cross-language round-trip, IDOR suite, `TestEthicsE5`, k-anonymity |
| `speech` | 188 tests, lint, PPI monotonicity + disfluency-invariance fairness gates |
| `genai` | 41 tests, lint, `TestDisfluencyInvariance` |
| `platform` | 83 tests, lint, redaction policy + fail-closed service auth |
| `web` | 478 tests, lint, typecheck, build, axe sweep across every channel, every input mode **and every real screen** |
| `ethics` | All 7 charter rules present; **every path the charter cites exists** |

**1,089 tests** (299 + 188 + 41 + 83 + 478), plus the 20 contract checks. Nothing merges
without all seven jobs green.

> A previous revision of this file claimed 825. It did not reconcile with the per-job
> numbers beside it and was wrong. The figure above is the sum of the row above it, and
> should be recomputed the same way whenever it changes — a headline number nobody can
> re-derive is worse than no number.

---

## Rules that keep this file honest

1. **Update it in the same commit as the work.** A status page updated separately is a status page nobody trusts.
2. **"Done" means a learner can reach it.** Not "the tests pass".
3. **A gap with no owner and no trigger is a wish.** Every 🔴 and 🟠 row names the module that closes it.
4. **Do not delete a gap because it is embarrassing.** The 🔴 rows are the most useful lines on this page.
5. **When a gap closes, move it into "Closed since the last update" rather than deleting it.** Knowing what was fixed and when is how the next person judges whether the rest of this page is trustworthy.

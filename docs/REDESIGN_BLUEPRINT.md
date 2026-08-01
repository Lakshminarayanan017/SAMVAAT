# SAMVAAD — Redesign Blueprint

**"The Duolingo of communication skills for people with disabilities."**

**Document status:** Draft for review · **Version** 1.0 · **Date** 2026-08-01
**Author:** Engineering
**Read before:** writing any redesign code.
**Supersedes:** nothing. Extends `docs/EXECUTION_PLAN.md`, does not replace it.

---

## 0. How to read this document

This is a redesign blueprint, not a rewrite plan. That distinction is the single most
important sentence in the document and it is worth defending immediately.

After a full read of the repository — 6,332 lines of API, 8,217 lines of client, 7,009 lines of
speech service, 6,316 lines of GenAI service, 3,221 lines of shared packages, 817 tests across
seven CI jobs — the conclusion is not what a redesign brief usually produces.

**The architecture is right. The engineering is strong. The presentation layer is where the
product is losing.**

That conclusion has consequences. A blueprint that proposed rewriting the speech pipeline, the
contracts package or the consent ledger would be destroying work that is better than what would
replace it, in order to look decisive. What follows preserves roughly 85% of the existing
codebase, deletes almost nothing, and concentrates effort on the ~4,000 lines of client feature
code where the "adventure game, not dashboard" gap actually lives.

| Section | Read it when |
|---|---|
| 1–2 | You want the verdict and the honest conflicts. **Read these two even if you read nothing else.** |
| 3 | Per-folder analysis. Reference material during implementation. |
| 4 | Gap analysis table. Sprint planning. |
| 5–7 | The product experience: world map, emotional journey, gameplay. |
| 8 | The mascot evaluation. |
| 9–11 | Design system, motion, visual language. |
| 12 | Disability-first personalisation — the hardest and most important section. |
| 13 | Social stories redesign. |
| 14 | Reward and motivation engine. |
| 15 | Multilingual architecture. |
| 16 | AI system review. |
| 17 | The phased implementation plan. |
| 18 | Testing, risk, rollback. |

---

## 1. The verdict

### 1.1 What the repository already is

Judged against its own execution plan, SAMVAAD is at **13 modules done, 7 partial, 0 not
started**. Judged against comparable products, it has several things almost nothing else in the
accessibility-technology space has:

**A modality-neutral content architecture that actually holds.** `ContentBlock` stores meaning
plus representations and no chosen rendering. An ESLint boundary rule fails the build if feature
code imports a renderer directly. This is not a claim in a README — it is enforced, and it is the
reason a generated role-play turn can arrive as speech for one learner and as tappable symbols
for another with no branching in the feature code.

**Baseline-relative scoring with a fairness gate in CI.** The Personal Progress Index measures a
learner against their own rolling baseline. Two automated gates run on every build: monotonicity
(a learner who improves sees their number rise) and disfluency invariance (two learners improving
identically, one with a constant 25-point disfluency offset, get statistically indistinguishable
trajectories). These are properties of the maths, need no dataset, and run today.

**A bias-guarded interview rubric with four independent enforcement layers.** Input scrubbing so
the scorer never receives disfluency or timing; a schema with exactly six fields; an invariance
gate; and a persisted audit record naming what was and was not graded. The scrubbing layer is the
strong one — you cannot penalise what you never received.

**Security thinking that is genuinely above the norm.** Identity comes from the token and
`user_id` was removed from every request model so it cannot be passed by accident. The
k-anonymity implementation suppresses a cell when the cell *or its complement* falls below the
floor, which is the differencing attack that almost every "anonymised dashboard" gets wrong. The
erasure test walks the schema rather than a list of tables — and that test found a real bug where
`DELETE /auth/me` reported success while leaving the learner's real name in a trainer link.

**A status document that tells the truth.** `docs/STATUS.md` lists gaps, names the module that
closes each one, keeps closed gaps visible rather than deleting them, and in one place corrects
its own previously-wrong test count with an explanation of why the wrong number was worse than no
number. Documents like that are rarer than good code.

### 1.2 What it is not

**It does not feel like anything.**

The client is 4,037 lines of feature code carrying approximately 140 inline `style={{ }}`
objects across ten files. There is no component library, no shared primitives, no motion system,
no illustration, no character, no celebration, no sound, no sense of place. Every screen is a
correct, accessible, well-reasoned rectangle of text on a surface colour.

A learner opening it sees a tab bar and a list. They complete a practice session and a sentence
changes. Nothing arrives, nothing lands, nothing is won. There is no reason to come back tomorrow
that is not already a reason to come back to a spreadsheet.

This is not a criticism of the work — the accessibility architecture had to come first, and
building the delight layer on top of a correct foundation is far easier than retrofitting
correctness under a pretty one. But the gap between "technically excellent accessibility product"
and "product a disabled seventeen-year-old opens on the bus because they want to" is the entire
remaining distance, and it is not small.

### 1.3 The strategic reframing

The brief asks to replicate Duolingo's psychology. The single most useful thing to understand
about Duolingo is that **its engagement does not come from its graphics.** It comes from four
mechanics, in this order of importance:

1. **The session is short and the end is visible.** You always know how much is left.
2. **Something is always in motion.** A number, a bar, a crown, a streak. Progress is never
   invisible and never delayed.
3. **The next action is chosen for you.** There is no decision to make, so there is no friction
   before starting.
4. **Ending is rewarded, not starting.** The celebration is at the end of the unit of work, which
   is what makes finishing feel better than starting.

None of those four requires a mascot, particles, or a winding path. All four are *architecturally*
absent from SAMVAAD today, and all four can be added to the existing screens.

That is the strategic reframing: **the redesign is 70% information architecture and feedback
loops, 30% visual craft.** Doing the visual craft first produces a beautiful product that is
still not addictive. This blueprint sequences it accordingly.

---

## 2. Conflicts requiring a decision

The brief contains eleven requirements that collide with rules the repository currently enforces
with passing tests, or with the Ethics Charter that those tests implement. Every one of these is
resolvable, but not silently — each needs a decision recorded.

They are listed with the conflict stated plainly, and a recommendation. **Nothing in the
implementation plan in §17 depends on the more contentious ones until they are settled.**

### 2.1 Emotion detection 🔴 Cannot build as specified

**Brief asks for:** "Emotion detection" under the AI system.

**Conflict:** `facial_affect` is on the Ethics E2 exclusion list, and the charter states the
rubric is "structurally prevented" from scoring it. Affect recognition on a disabled population
is additionally a well-documented harm surface: autistic people, people with facial paralysis,
people with Parkinson's, people with cerebral palsy and people on certain medications all produce
facial and vocal affect that automated systems systematically misread. A system that told an
autistic learner their tone was "wrong" would be scoring their disability.

**What is buildable, and is genuinely valuable:**

| Buildable | Not buildable |
|---|---|
| Teaching the learner to **recognise** emotion in a scenario character (a comprehension lesson) | Measuring emotion in the learner's face |
| Learner **self-reporting** how a conversation felt (already the `confidence` PPI dimension) | Inferring emotion from the learner's voice |
| Character emotion in social stories **authored** by us and driven by the branch taken | Scoring the learner on emotional expression |

**Recommendation:** Build emotion as *curriculum content* and *self-report*, never as
measurement of the learner. Rename the feature "Emotion literacy" so nobody later reads
"emotion detection" in a backlog and builds the forbidden thing.

### 2.2 Confidence estimation 🟠 Build, but only from self-report

**Brief asks for:** "Confidence estimation".

**Conflict:** Inferring confidence acoustically means scoring voice quality and affect. Both are
excluded. It is also unreliable: quiet, flat or hesitant speech is a disability characteristic for
several personas and says nothing about how confident the person feels.

**Recommendation:** Confidence stays a self-reported 1–5, which the PPI already supports as a
weighted dimension. This is not a downgrade — self-report is the *more* valid instrument here, and
it is what the pilot's confidence outcome measure is based on anyway.

### 2.3 Body-language puzzles 🟠 Build as comprehension only

**Brief asks for:** "Body language puzzles".

**Conflict:** `body_posture`, `motor_stillness` and `gaze` are all excluded dimensions, and
Ethics E4 says video never leaves the device.

**Recommendation:** Build puzzles where the learner **reads** body language in an illustrated or
animated character — a genuinely useful workplace skill, and one several personas explicitly want.
Never build a puzzle that evaluates the learner's own body. If on-device pose estimation is ever
added it is a mirror for the learner's private use, never a score, and E4 governs it.

### 2.4 Confetti and particle effects 🟠 Build, opt-in, off by default

**Brief asks for:** "Particle effects. Confetti."

**Conflict:** Large numbers of independently moving objects is the single worst pattern for
vestibular sensitivity. Vestibular disorders are common and under-declared, and a celebration that
causes nausea closes the app permanently.

**Recommendation:** Ship a celebration system with three levels the learner controls —
**Full** (bounded particle burst, ≤24 particles, single emission, no loop), **Gentle** (stars land,
no particles — the default), and **Still** (cross-fade only). `prefers-reduced-motion` forces
Still unless the learner has explicitly overridden it in-app. This gives the brief its confetti
without making it the default experience for a population disproportionately likely to be harmed
by it.

### 2.5 Coins and unlockables 🟢 Build, with one hard rule

**Recommendation:** Coins are cosmetic-only currency. **No coin, gem, or unlock may ever gate
learning content.** The moment a learner cannot reach a lesson without a currency, the product has
invented a failure wall — which the brief itself forbids two sections later. Coins buy mascot
outfits, world themes, and avatar parts. Nothing else.

### 2.6 Mastery checkpoints and boss challenges 🟢 Build as soft gates

**Conflict:** Ethics E7 — a feature that fails a persona is not shippable. A gate a learner cannot
pass fails them permanently, and the learner most likely to need interview practice *tomorrow* is
the one least likely to have time for fifty levels first.

**Recommendation:** Already resolved in the shipped progression engine and worth restating.
Mastery gates **stars**, which are optional. It never gates **access**, which is not. A level
ahead of you is `AVAILABLE_EARLY` with the caption "Further on — you can still try it", never
`LOCKED` with a padlock. A padlock on a product built for disabled people reads as "not for you".

### 2.7 Age at onboarding 🟠 Ask for a band, and only because of guardianship

**Conflict:** DPDP Act 2023 data minimisation. Collecting a date of birth requires a purpose.

**Recommendation:** Ask "Are you under 18?" as a yes/no, once, because it changes a real thing —
guardian consent flow. Do not collect date of birth. Do not use age to change lesson content;
"content for your age group" is a paternalism trap for adults with intellectual disabilities, who
are routinely handed children's material.

### 2.8 Weakness prediction and progress forecasting 🟠 Reframe

**Conflict:** Forecasting produces a predicted ceiling. Showing a disabled learner a predicted
ceiling is a self-fulfilling prophecy with a progress bar attached, and it is a short walk from
there to an institution using the forecast to decide who gets a placement.

**Recommendation:** Build *"what to practise next"* — which already exists, is explainable, and is
the actionable half. Never surface a predicted score, a predicted date, or a predicted ceiling to
a learner, a trainer or an institution.

### 2.9 Public leaderboards 🔴 Do not build

The brief itself says "No public leaderboards", and the repository agrees with a passing test.
Recorded here only so a future reader does not reintroduce them via "leagues" or "tournaments".
**Tournaments against the AI are fine and are in the plan.** Tournaments against other learners
are not.

### 2.10 WCAG 2.2 AAA 🟠 Target it, and document what is unreachable

**Conflict:** The repository targets AA. AAA is a real step up and two success criteria are
genuinely unreachable for this product:

- **1.2.6 Sign Language (Prerecorded)** — requires ISL for *all* prerecorded audio. At 226 phrases
  plus generated role-play, this is a content and human cost, not a code one. Partially achievable
  (top 100 phrases), never fully.
- **3.1.5 Reading Level** — requires lower-secondary reading level for all content. Interview
  questions and the RPwD rights primer cannot be reduced that far without destroying their
  meaning. The Easy-Read channel is the compensating mechanism, and it is stronger than the SC.

**Recommendation:** Target AAA for everything achievable — 1.4.6 contrast 7:1 (already met by the
new world palettes), 2.2.3 no timing (already met and enforced), 2.3.2 three flashes (met), 2.4.9
link purpose, 3.3.5 help available. Publish a conformance statement naming 1.2.6 and 3.1.5 as
partial with the reason. A published honest AAA-minus-two is worth more than an unpublished AAA
claim nobody audited.

### 2.11 Twelve languages 🟠 Split into four tiers with very different costs

This is the largest hidden cost in the brief and it must not be estimated as one number.

| Tier | What it means | Cost | Feasible by pilot? |
|---|---|---|---|
| **UI strings** | Buttons, labels, navigation | Low — ~600 strings, standard i18n | Yes, all 12 |
| **AI explanation language** | The model explains in the learner's language | Very low — a prompt parameter | Yes, all 12 |
| **Phrase bank translation** | 226 phrases, culturally adapted not literally translated | **High** — needs a native speaker per language, and workplace idiom does not translate | Tamil + Hindi realistically |
| **Speech analysis** | G2P, phoneme inventory, acoustic model per language | **Very high** — a research project per language | English only, honestly |

**Recommendation:** Architect for all twelve from day one (§15 specifies how), ship UI and AI
explanation in all twelve, ship the phrase bank in English + Tamil + Hindi, and be explicit in the
UI that speech analysis is English-only for now. A learner who is told plainly will accept it. A
learner who discovers it by having their Tamil scored as bad English will not.

### 2.12 Summary of decisions needed

| # | Item | Recommendation | Needs your call? |
|---|---|---|---|
| 2.1 | Emotion detection | Curriculum + self-report only | **Yes** |
| 2.2 | Confidence estimation | Self-report only | No |
| 2.3 | Body language | Comprehension only | **Yes** |
| 2.4 | Confetti | Three levels, Gentle default | **Yes** |
| 2.5 | Coins | Cosmetic only, never gate content | No |
| 2.6 | Boss/mastery | Soft gates | No |
| 2.7 | Age | Band only, for guardianship | No |
| 2.8 | Forecasting | Reframe to "next" | **Yes** |
| 2.9 | Leaderboards | Do not build | No |
| 2.10 | AAA | Target, publish exceptions | No |
| 2.11 | Languages | Four tiers | **Yes** |

---

## 3. Repository analysis, folder by folder

### 3.1 `packages/contracts` — ★ the load-bearing package

**What exists.** JSON Schema as the single source of truth for `ContentBlock`,
`LearnerResponse` and `CommunicationAbilityProfile`. TypeScript types and Pydantic models are
generated from it; a drift check fails CI if generated output diverges. Runtime guards
(`normaliseText`, `channelsFor`, `resolveChannel`, `FALLBACK_CHAIN`) encode contract *behaviour*
that schema cannot express. Fixtures include deliberately invalid and deliberately inaccessible
blocks that CI must reject.

**What works well.** Nearly everything. `normaliseText` living here rather than in each consumer
is exactly right — if the client and the scoring engine normalised differently, learners would be
marked wrong for reasons nobody could see. The a11y rule set (A11Y-1 to A11Y-6) that fails a
`ContentBlock` requiring a channel a persona lacks is the mechanism behind the entire
accessibility claim.

**Preserve.** All of it. Do not touch the generation pipeline.

**Redesign.** `CommunicationAbilityProfile` needs three additive fields for the redesign:
`learning_profile_id` (which preset was chosen — nullable, never a diagnosis),
`motion_preference` (`full | gentle | still`), and `celebration_level`. All additive, all
optional, so no migration breaks.

**New.** A fourth schema, `LessonMission`, describing a single gameplay mission and its accepted
answer shapes. Currently mission types are strings in the curriculum JSON with no schema behind
them; as gameplay grows this becomes a source of silent breakage.

**Technical debt.** None material.

**Risk.** This package is the one place where a careless change breaks every service at once.
Any change needs the existing two-track approval rule.

### 3.2 `packages/content` — the corpus and now the curriculum

**What exists.** 226 phrases across 14 categories in a compact authoring format, expanded to full
`ContentBlock`s by a build script. Easy-Read linter, ARASAAC symbol resolution, G2P-generated
phonemes (226/226 done). As of the most recent work: `curriculum/worlds.json` (10 worlds, 15
chapters, 50 levels) and `curriculum/profiles.json` (13 learning presets), resolved against the
real phrase bank at build time.

**What works well.** The compact authoring format is a genuinely good decision — 30 lines of JSON
per phrase × 226 guarantees copy-paste errors and guarantees nobody proof-reads the English. The
curriculum resolving *category slices* rather than hard-listed phrase ids means the journey cannot
drift from the corpus, and a stale reference fails the build.

**Preserve.** The authoring format, the build/validate split, the a11y gate.

**Redesign.** The curriculum data currently describes *which phrases* a level contains but not
*what happens* in it. Missions are named but not specified. This needs to grow into a mission
specification (see §10).

**Remove.** Nothing.

**New — and this is the largest content gap in the project:**

| Asset | Have | Need | Blocker |
|---|---|---|---|
| Phonemes | 226/226 | — | done |
| Audio (native + slow) | 0/452 | 452 files | TTS bootstrap — **not blocked, just not done** |
| ISL clips | 3/226 | 100 priority | **A Deaf signer. Long lead time. Start outreach now.** |
| Pictograph verification | 0/226 human-checked | 226 | Human review; automatic mapping produces embarrassing results |
| Story scenes | 0 | ~14 branching stories | Authoring + illustration |
| Character art | 0 | ~8 workplace characters | Illustrator |
| Mascot art | 1 SVG | ~20 states | Illustrator |

**Accessibility concern.** Zero audio files is the most serious content gap. Two personas (P1 low
vision, P4 intellectual disability) depend on the audio channel, and the modality router currently
falls back to captions for them. The product claims five output channels and can genuinely serve
four. TTS bootstrap closes this in days and is the highest-value content task in the plan.

**Performance concern.** The built `blocks.json` is inlined into the client bundle in the original
`main.tsx` — already fixed by the offline work, which fetches and caches it. Verify this stays
fixed; it is an easy regression.

### 3.3 `packages/platform` — cross-service primitives

**What exists.** Structured JSON logging with redaction applied at the formatter, request-id
tracing across services, a shared error shape with learner-facing messages, token-bucket rate
limiting with limits on expensive operations only, service-to-service token auth that fails closed
in production, security headers. 53 tests.

**What works well.** Redaction at the formatter rather than the call site is the correct call and
the comment explaining why ("a rule that depends on every developer remembering it has a half-life
of about four months") is the kind of reasoning that keeps a codebase honest. The rate-limit
design note — that limits sit on expensive operations and not on interactions, because a switch-
scanning learner generates far more UI events than a mouse user — is a genuinely subtle
accessibility insight most teams would miss.

**Preserve.** All of it.

**New.** Two additions for the redesign: a **feature-flag primitive** (needed for phased rollout
and for the celebration-level experiment), and a **product-analytics event schema** with the same
redaction guarantees. PostHog is planned in M19 and must never receive content.

**Scalability concern.** `TokenBucket.is_distributed` is `False` and honest about it. On multiple
instances the limiter is per-instance. This is correct for the free tier and needs a Redis
implementation before horizontal scaling. Documented; not urgent.

### 3.4 `apps/api` — the gateway

**What exists.** FastAPI, 6,332 lines. SQLAlchemy async models (users, CAP versions, consent
ledger, cards, conversations, speech attempts, audit), repositories, JWT auth with guest-first
sessions, and eleven routers: health, auth, content, practice, audio, conversation, profile,
progress, journey, trainer, institution, export.

**What works well.**

- **Auth.** Identity from the token, `user_id` removed from every request model, IDOR regression
  suite. Guest-first is a product decision as much as a security one and the reasoning is right.
- **The learning modules.** FSRS is a real implementation of the published algorithm, not SM-2.
  `grading.py` derives a grade from observable behaviour and *cannot see timing* — enforcement by
  function signature, which is the strongest kind. `session.py`'s morale constraints (max two hard
  items, always open with a likely win) are the kind of thing that only comes from thinking about
  a real learner having a bad week.
- **`anonymity.py`.** The complement-suppression logic is better than most production analytics.
- **Export/erasure.** The schema-walking erasure test is exemplary and already caught a real bug.

**Preserve.** Effectively all of it. This is the strongest part of the codebase.

**Redesign.** Three things:

1. **`progress.py` recomputes XP from card history on every request** — walking every card,
   fetching every block, summing. Correct, defensible ("a stored counter that disagrees with the
   history is a counter nobody can defend"), and O(cards) per page load. At 226 cards it is fine;
   at 2,000 (post-multilingual) on a free-tier dyno it will be felt. Needs a materialised
   projection with the recompute retained as the source of truth and a reconciliation job.
2. **`journey.py` and `progress.py` overlap.** Both build a picture of learner progress from
   cards. They should share one projection.
3. **Conversation state is in-memory behind a Protocol** in `conversations.py` while `ConversationRow`
   exists in the schema. Verify which is live; if the in-memory one is, an interview does not
   survive a redeploy, which breaks the E6 pause-and-resume claim.

**New routers needed:** `missions` (gameplay), `stories` (branching state), `rewards`
(coins, unlockables, avatar), `i18n` (locale bundles).

**Technical debt.** `pyjwt` is declared twice in `requirements.txt`, once with the `[crypto]`
extra and once without. Harmless today; whichever pip resolves last decides whether RS256 works.
One-line fix.

**Scalability concern.** No Alembic migrations — `create_all` is correct for SQLite dev and
cannot alter a table. The first Postgres deployment needs Alembic *before* it happens, not after.
This is on the STATUS.md accepted list and the trigger is correct.

**Security concern.** No row-level security. Application-layer authorisation is thorough and
tested, so this is defence-in-depth rather than an open hole, but the charter's data model
specifies RLS and it remains unbuilt.

### 3.5 `apps/web` — where the redesign lives

**What exists.** React 18 + Vite, 8,217 lines. Modality router with five output renderers and five
input adapters, design tokens with four themes, `<Announcer/>`, switch-scan driver, audio capture
with quality metering, offline shell (service worker, IndexedDB, append-only outbox), and ten
feature screens.

**What works well.**

- **The modality layer.** This is genuinely excellent and is the product's moat. Do not touch it.
- **`a11y/`.** The announcer, the profile provider, and `useSwitchScan` are correct and carefully
  reasoned.
- **`offline/`.** Append-only outbox, oldest-first replay, nothing leaves until the server
  confirms. Correct design.
- **`design-system/tokens.ts`.** Four themes, contrast verified by unit test rather than asserted
  in a comment. The border colour comment — that the obvious `#9aa3ad` manages only 2.56:1 —
  is the sort of detail that separates real accessibility work from a checklist.

**Redesign — this is the bulk of the work.**

The ten feature screens carry ~140 inline `style={{ }}` objects. Every screen re-invents its own
card, its own button, its own spacing. There is no `<Button>`, no `<Card>`, no `<Stack>`, no
`<ProgressBar>`. Consequences:

- **Inconsistency is guaranteed.** Ten screens will drift because nothing holds them together.
- **Theming is partially bypassed.** Inline styles reference CSS custom properties (good) but
  hard-code layout values (not good), so the 400% zoom reflow requirement is per-screen luck.
- **No animation is possible.** You cannot add a motion system to inline style objects without
  touching every one of them.
- **`ChannelComparison.tsx` at 305 lines with 27 inline style objects** is the worst offender and
  is a demo surface, not a learner surface.

**What should be rewritten:** the presentation of all ten feature screens, on top of a new
component layer. Not their logic — their logic is fine and mostly already correct. This is a
re-skin with an information-architecture change, not a functional rewrite.

**What should be removed:** `features/channel-comparison/` should move out of the learner
navigation. It is a superb *pitch* artefact — one block rendered through five channels with a
persona switcher — and it is not a thing a learner needs in their tab bar. Move to `/demo`.

**New modules needed:** `ui/` (primitives), `game/` (map, level runner, celebration — partially
started), `story/` (branching engine), `rewards/`, `i18n/`, `illustration/`.

**Performance concern.** No code splitting. Every screen, the offline shell and the whole design
system are in one bundle. Our learners are explicitly on entry-level Android and low bandwidth.
Route-level splitting is required, and it needs a router first.

**Accessibility concern.** No client-side router means no shareable URLs, no back button, and a
tab-based information architecture that will not survive ten worlds × five chapters. The STATUS.md
entry is honest that the trigger is "a surface somebody needs to link to" — **the redesign is that
trigger.** A trainer assigning a level to a learner needs a link.

### 3.6 `services/speech`

**What exists.** 7,009 lines. Preprocessing with honest rejection, G2P with a real availability
probe, CTC forced alignment over a phoneme model, GOP as pure testable maths, prosody as
deterministic signal processing, a disfluency classifier interface awaiting weights, per-learner
ASR adapter machinery with a never-regress guardrail, and the PPI with its two fairness gates.

**What works well.** The optional-backend probing pattern means the service boots in seconds with
nothing installed and reports honestly what it can do. The separation of GOP (pure maths over a
matrix) from the model that produces the matrix is what makes the fairness properties testable at
all.

**Preserve.** All of it.

**Redesign.** Nothing structural. Two integration tasks: the disfluency weights need to be
installed once training runs, and prosody needs to be surfaced into the gameplay loop as coaching
cues rather than sitting behind an API nothing calls.

**Blocked, not broken.** M7's classifier needs a SEP-28k training run; M8's LoRA needs UASpeech
access with a 2–4 week turnaround that has not been requested. **Requesting UASpeech access is a
zero-cost action that should happen this week regardless of anything else in this blueprint.**

### 3.7 `services/genai`

**What exists.** 6,316 lines. Provider interface with Claude primary and a first-class scripted
fallback, versioned hashed prompts, RAG over the phrase bank, a six-check guardrail chain
including a condescension filter, role-play engine, social story generator with a Carol Gray
structural validator, mock interview runner, bias-guarded rubric, disclosure coach.

**What works well.** The scripted provider being a first-class path rather than a mock is the
right call and pays off four ways (outage, budget, CI, offline). The condescension filter is
something no comparable product has. The rubric's refusal to invent a score when no model is
available — rather than producing a plausible fake — is exactly right.

**Preserve.** All of it.

**Redesign.** The role-play engine and the story generator both need to feed the new gameplay and
branching-story layers rather than being standalone endpoints. The interview runner needs to
become a mission type.

**Cost concern.** The budget system is sound but untested against real usage. A cost model per
active learner per day should be built before the pilot, not after the first invoice.

### 3.8 `docs`

**What exists.** Execution plan (90KB), ethics charter, accessibility criteria, five personas,
seven ADRs, and an exemplary STATUS.md.

**Preserve.** All of it. The charter in particular is load-bearing — CI reads it.

**New.** This blueprint, a design-system document, a conformance statement (§2.10), an emotion-
literacy design note recording the §2.1 decision, and ADRs for each of the §2 decisions taken.

### 3.9 Cross-cutting summary

| Area | Preserve | Redesign | Rewrite | Remove |
|---|---|---|---|---|
| `packages/contracts` | 100% | additive fields | — | — |
| `packages/content` | 100% | curriculum grows | — | — |
| `packages/platform` | 100% | + flags, analytics | — | — |
| `apps/api` | ~95% | progress projection | — | — |
| `apps/web` **logic** | ~90% | routing, splitting | — | — |
| `apps/web` **presentation** | ~10% | — | **all ten screens** | channel-comparison from nav |
| `services/speech` | 100% | — | — | — |
| `services/genai` | 100% | integration surface | — | — |

**Roughly 85% preserved. One layer rewritten.**

---

## 4. Gap analysis

Priority: **P0** blocks the redesign thesis · **P1** required for pilot · **P2** required for the
award/competition claim · **P3** post-pilot.

Effort: **S** ≤3 days · **M** ~1–2 weeks · **L** ~3–4 weeks · **XL** ~2 months+.

### 4.1 Foundation gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk | Strategy |
|---|---|---|---|---|---|---|---|---|
| F1 | **No UI primitives** | ~140 inline style objects | `ui/` with Button, Card, Stack, Text, ProgressBar, Icon, Sheet, Dialog | P0 | M | — | Low | Build primitives first, migrate screens one per PR behind no flag — pure refactor, tests unchanged |
| F2 | **No client router** | Tab state in `App.tsx` | Route-per-surface, focus + title + announcement on change | P0 | M | F1 | **Med** — a11y regression risk | Build the accessible route wrapper once (focus move, `aria-live` announce, document title); every route uses it or fails a test |
| F3 | **No code splitting** | One bundle | Route-level lazy, ≤120KB initial JS | P0 | S | F2 | Low | Vite dynamic import per route + skeleton |
| F4 | **No motion system** | None | Tokens + keyframes + reduced-motion enforcement | P0 | S | F1 | Low | Started; extend |
| F5 | **No design language** | Tokens only | Full system: colour, type scale, elevation, illustration, iconography | P0 | M | F1 | Low | §9 |
| F6 | **No feature flags** | None | Platform primitive + client hook | P1 | S | — | Low | Simple config-backed, no vendor |

### 4.2 Game layer gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk | Strategy |
|---|---|---|---|---|---|---|---|---|
| G1 | **World map not wired** | Component built, not in app | Home screen | P0 | S | F2 | Low | Replace tab bar |
| G2 | **No level runner** | Practice session only | Mission sequencer with intro, missions, outro | P0 | L | F1,G1 | Med | §10 |
| G3 | **No mission types** | One (recognise/produce implicit) | Eight typed missions | P0 | L | G2 | Med | Build 3 first (recognise, choose, produce), then 5 |
| G4 | **No celebration** | None | Star landing, XP count, mascot, three intensity levels | P0 | M | F4,G2 | Low | §14 |
| G5 | **No daily goal** | None | Session-length goal, visible, non-punishing | P1 | S | G2 | Low | Reuse `session_length_target_min` |
| G6 | **No quests** | None | Daily/weekly quests | P1 | M | G4 | Low | Derived from existing telemetry |
| G7 | **No skill tree** | Linear worlds | Branching optional mastery paths | P2 | L | G3 | Med | Post-pilot |
| G8 | **No AI tournament** | None | Timed-free challenge vs AI | P3 | M | G3 | Low | Explicitly never vs learners |

### 4.3 Personalisation gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk | Strategy |
|---|---|---|---|---|---|---|---|---|
| P1 | **Profiles not in onboarding** | 13 presets exist as data | Chosen during onboarding | P0 | M | F2 | Med | §12 |
| P2 | **Profiles don't drive missions** | Weights are data only | Mission mix per profile | P0 | M | G3,P1 | Med | §12.4 |
| P3 | **Profiles don't drive AI** | One prompt for all | Per-profile system prompt fragments | P1 | M | P1 | **Med** — prompt sprawl | Compose from fragments, hash each |
| P4 | **No strategy surfacing** | 40 strategies as data | Delivered as coaching in context | P1 | M | P1 | Low | Tie to mission outcome |
| P5 | **3 profiles missing** | 13 | + ADHD, selective mutism, speech delay | P1 | S | P1 | Low | §12.2 |
| P6 | **No profile change flow** | — | Change from settings in ≤2 actions | P1 | S | P1 | Low | Charter requirement |

### 4.4 Story gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk | Strategy |
|---|---|---|---|---|---|---|---|---|
| S1 | **Stories are linear panels** | 6–10 panels, no choice | Branching scenes with consequence | P1 | L | F1 | Med | §13 |
| S2 | **No characters** | None | 8 recurring workplace characters | P1 | L | S1 | **Med** — illustration cost | Commission or build a constrained SVG system |
| S3 | **No character emotion** | None | Authored expression per branch | P1 | M | S2 | Low | Expression = data, not inference |
| S4 | **No replay/endings** | — | Replayable, multiple endings | P2 | M | S1 | Low | Branch state persisted |
| S5 | **6 preset situations** | Fixed list | Trainer-authored situations | P2 | M | S1 | Low | Keeps learner input an index, not prose |

### 4.5 Reward gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk |
|---|---|---|---|---|---|---|---|
| R1 | **XP invisible** | Computed, shown as a number | Animated, earned in front of you | P0 | S | G4 | Low |
| R2 | **No coins** | None | Cosmetic currency | P2 | M | R1 | Low |
| R3 | **No avatar** | None | Learner avatar + mascot outfits | P2 | L | R2 | Low |
| R4 | **No titles** | None | Earned titles | P3 | S | R1 | Low |
| R5 | **Badges not celebrated** | Returned in JSON | Awarded with a moment | P1 | S | G4 | Low |

### 4.6 Content gaps

| # | Gap | Current | Desired | Pri | Eff | Depends | Risk |
|---|---|---|---|---|---|---|---|
| C1 | **No audio** | 0/452 | TTS bootstrap all, human top-100 | **P0** | S | — | **Low — do this first** |
| C2 | **ISL clips** | 3/226 | 100 | P1 | XL | Deaf signer | **High — long lead** |
| C3 | **Pictographs unverified** | 0/226 | 226 | P1 | M | Human review | Med |
| C4 | **Mascot art** | 1 SVG | ~20 states | P1 | M | §8 | Low |
| C5 | **Character art** | 0 | 8 characters × 5 expressions | P1 | L | S2 | Med |
| C6 | **No sound design** | None | UI + celebration sounds, off by default | P2 | M | — | Low |

### 4.7 Platform gaps

| # | Gap | Current | Desired | Pri | Eff | Risk |
|---|---|---|---|---|---|---|
| X1 | **No i18n** | English hard-coded | 12 locales, 4 tiers | P1 | L | Med |
| X2 | **No Alembic** | `create_all` | Migrations | P1 | S | **High if deferred past first Postgres deploy** |
| X3 | **No RLS** | App-layer only | Postgres RLS | P2 | M | Med |
| X4 | **No analytics** | None | PostHog, redacted, schema-first | P1 | M | Low |
| X5 | **No error tracking** | Logs only | Sentry with scrubbing | P1 | S | Low |
| X6 | **On-device ASR** | Not started | onnxruntime-web | P2 | L | Med |
| X7 | **ISL recognition** | Not started | MediaPipe + classifier | P2 | XL | **High — blocks E4 test** |
| X8 | **No manual SR passes** | axe only | NVDA/VoiceOver/TalkBack | **P1** | M | **High — axe catches ~30%** |

---

## 5. The product experience

### 5.1 The emotional journey

The redesign should be evaluated against a single narrative. This is the story the product must
make true.

**Day 0 — Arrival.** A learner opens SAMVAAD, probably because a trainer or a parent suggested it,
probably sceptical, probably having been handed inaccessible training before. The first screen
does not ask them to sign up. It asks them, in four huge self-narrating targets, how they would
like to be spoken to. Within thirty seconds the app is speaking their language, at their pace, in
their channel. **The emotional beat: "this was built for me, not adapted for me."**

**Day 0, +2 minutes — The first win.** Not a tutorial. A single mission, in World 1, that they
complete successfully. Mitra reacts. A star lands. XP counts up in front of them. **The emotional
beat: "I did that."** This must happen before any account, any form, any explanation.

**Day 0, +5 minutes — The map.** Now they see ten worlds, and they see that the last one is *The
Interview*, and they see it is not locked. **The emotional beat: "that is where this goes, and it
is for me."**

**Day 1 — The return.** Not a guilt notification. Mitra, in the notification, saying something
specific and warm about what is next — not what was missed. **The emotional beat: "something is
waiting for me", never "I let something down."**

**Week 2 — The first third star.** They come back to a level they finished a fortnight ago and
every phrase is still there. The third star lands. **The emotional beat: "it stuck. I actually
learned this."** This is the moment the product's core claim becomes felt rather than asserted.

**Week 4 — The baseline crossing.** Their PPI chart shows their own line, and today they are above
it. **The emotional beat: "I am better than I was."** Not better than anyone. Better than they
were.

**Week 8 — The disclosure rehearsal.** They open World 5, Chapter 2, and rehearse telling an
employer what helps them work. They practise the branch where it goes badly. **The emotional beat:
"I have said this out loud before. I can say it again."**

**Week 12 — The interview.** They complete a full mock interview. The feedback leads with
strengths, names two things to try, and says nothing whatsoever about how they spoke. **The
emotional beat: "I was judged on what I said."** For many learners this will be the first time.

Every design decision in this blueprint should be checkable against that story. If a feature does
not advance one of those beats, it is decoration.

### 5.2 The session shape

The core loop. Target: **3–7 minutes**, adjustable by profile from 4 to 8.

```
  OPEN APP
     ↓
  HOME / MAP  ──── "Continue" is the largest thing on the screen
     ↓            (no decision required — the next level is chosen)
  LEVEL INTRO ─── what you will practise · how many missions · Mitra
     ↓            ~8 seconds, skippable, never shown twice for the same level
  MISSION 1 ───┐
  MISSION 2    │  3–6 missions, mixed types, chosen by profile weights
  MISSION 3 ───┘  progress dots visible throughout — the end is always in sight
     ↓
  LEVEL OUTRO ─── stars land · XP counts · Mitra reacts · badge if earned
     ↓            THIS IS THE PAYOFF. It gets the 420ms.
  NEXT? ───────── "One more" is the primary action. "Done for today" is equal weight,
                  never smaller, never grey.
```

**Design rules for the loop:**

1. **The end is always visible.** Progress dots, not a spinner. A learner must always be able to
   answer "how much is left" without asking.
2. **No decision before starting.** "Continue" resolves to a specific level. Choosing is available
   and never required.
3. **The celebration is at the END of the unit of work.** Not per mission. Celebrating every
   correct answer devalues the currency and lengthens the session by 40%.
4. **"Done for today" is a first-class button.** Equal visual weight to "one more". A product for
   people with fatigue conditions that makes stopping feel like quitting is a product that
   punishes fatigue.

### 5.3 Information architecture

Replacing the six-tab bar:

```
/                     Home — the map, "continue", daily goal, streak, Mitra
/world/:id            World detail — chapters, levels
/level/:id            Level runner (full-screen, no chrome)
/story/:id            Story runner (full-screen)
/interview            Interview (full-screen)
/me                   Progress — PPI chart, phrases, badges, avatar
/me/data              Your data (export, erasure, consent)
/me/settings          How the app talks to me
/trainer              Trainer dashboard (role-gated)
/institution          Cohort report (role-gated)
/demo                 Channel comparison (moved out of learner nav)
```

**Four surfaces are full-screen with no chrome** — level, story, interview, onboarding. This is
the "not a dashboard" change, and it is structural rather than cosmetic. A learner mid-mission
should see the mission and nothing else.

**The route wrapper is a shared accessibility component**, not per-route code. On every route
change it moves focus to the new `<main>`, announces the destination via `aria-live`, and updates
`document.title`. A route that does not use it fails a test. This is the single largest
accessibility risk in the redesign and it is closed by making the safe path the only path.

---

## 6. The world map

### 6.1 Why a list and not a winding path

The obvious design is the snaking trail of nodes. It is worth explaining precisely why it is
rejected, because it will be proposed again.

A winding path encodes order in two-dimensional position. That means:

- A screen reader receives a sequence of buttons with **no spatial information** — the curve
  conveys nothing.
- Switch scanning must traverse a **zig-zag**, which row-column scanning handles badly.
- At the **400% zoom WCAG 2.2 requires**, the path either breaks or forces scrolling in two
  directions, which is a 1.4.10 Reflow failure.
- On a narrow phone, the path compresses to near-vertical anyway — so the aesthetic is lost
  exactly where most learners are.

Each of those hits a persona the product exists for. A vertical list of worlds, each expanding
into chapters and levels, carries identical information and reflows, scans and reads correctly
with no special handling.

**The delight comes from world identity, stars, motion and Mitra — none of which need a curve.**

A `[V2]` decorative path drawn *behind* an already-correct list is a fine idea, and is in the P3
backlog. Building the path first and retrofitting accessibility is not.

### 6.2 Ten worlds

Already built and resolved against the corpus. Restated for reference:

| # | World | Covers | Flagship |
|---|---|---|---|
| 1 | Finding Your Voice | greetings | |
| 2 | Making Sure You Understand | clarification | |
| 3 | Saying Where You Are | progress reporting | |
| 4 | Asking For What You Need | requesting help | |
| 5 | **Speaking Up For Yourself** | adjustments + self-advocacy | ★ |
| 6 | Handling Disagreement | disagreeing + feedback | |
| 7 | On The Phone And In Writing | telephone + written | |
| 8 | In The Room | meetings + small talk | |
| 9 | When It Matters | safety | |
| 10 | **The Interview** | interview language | ★ |

The two flagship worlds are the two nothing else on the market teaches. They lead the demo.

### 6.3 Triple-encoded identity

Every world carries three independent signals, so the map works with no colour at all:

1. **Colour** — ten palettes, each verified at 7:1 (AAA) in light and dark by unit test.
2. **Icon silhouette** — chosen to differ in *outline* at 32px monochrome, not merely in detail.
3. **Number and name** — always text, never decoration.

Roughly one man in twelve has a colour vision deficiency. A map that encodes identity only in hue
tells them nothing.

---

## 7. Gameplay

### 7.1 The principle

Communication practice becomes gameplay when the learner is **solving** rather than **answering**.
The difference is whether there is a *situation* with a *constraint*.

- "Which of these means 'please repeat'?" — a quiz question.
- "Your supervisor said three things and the machine was loud. You caught the first. What do you
  say?" — a puzzle.

Same phrase, same recall, entirely different experience. **Every mission type below is framed as a
situation with a constraint.**

### 7.2 Eight mission types

| Type | The verb | Constraint that makes it a puzzle | Channels | Profile fit |
|---|---|---|---|---|
| **Match it** (`recognise`) | Connect meaning to phrase | Distractors are *plausible*, drawn from `common_errors` | all | Universal — the floor |
| **What fits here** (`choose_in_context`) | Pick the phrase the room expects | Three are all *grammatically correct*; only one fits the relationship | all | Autism ★, ID |
| **Say it your way** (`produce`) | Produce the phrase | Any channel. Never "say it correctly" — "say it so it lands" | all | Universal |
| **Put it in order** (`order_the_steps`) | Sequence an exchange | The pieces are a real conversation, out of order | text/AAC/switch | Down-weighted for blind (drag) |
| **Live it** (`scenario`) | Choose a response, see consequence | Branching. The world reacts | all | Universal |
| **Talk it through** (`roleplay`) | Multi-turn conversation | AI colleague, grounded in world phrases | all | Anxiety ★, stammer ★ |
| **The real thing** (`interview`) | Full mock interview | World 10 only | all | Universal |
| **Show what you can do** (`boss`) | Mixed challenge | Draws from the whole chapter | all | Universal |

### 7.3 Two new mission types the brief implies

**Emotion literacy** (`read_the_room`) — an illustrated character says a line with an authored
expression and context. The learner identifies what the character means or feels. **This measures
the learner's comprehension of an authored character, never the learner's own affect.** This is
the buildable half of §2.1 and it is a genuinely requested skill for autistic learners.

**Listening** (`catch_it`) — audio (or captions, or ISL) plays once. The learner identifies what
was asked. Deliberately *not* timed — the replay button is unlimited and prominent. The constraint
is noise or ambiguity, never time.

### 7.4 What makes a mission accessible by construction

Every mission type must satisfy five properties, checked by a shared test harness:

1. **Answerable in every input channel the learner's profile offers.** A mission with only one
   answer path is a mission that excludes a persona.
2. **No time limit anywhere.** Not a countdown, not a bonus, not a "you took a while" prompt.
3. **Unlimited retries with no cost.** No hearts, no lives, no progress lost.
4. **A scaffold available at all times** — hint, sentence starter, or three choices. Requesting a
   scaffold reduces the FSRS grade (genuine partial recall) and **never** reduces XP.
5. **Wrong answers produce coaching, never a verdict.** "Not quite yet — here is what fits" and
   the reason.

### 7.5 Quests

- **Daily goal** — derived from the learner's own `session_length_target_min`, not a fixed number.
  Missing it produces nothing. No red, no zero, no "you missed".
- **Daily quest** — one, varied, achievable inside the daily goal ("finish a level in World 3",
  "try a phrase you found hard").
- **Weekly quest** — three, one of which is always a *courage* quest (attempt something above
  level, replay a story with a different choice, practise disclosure).
- **Seasonal campaign** — a themed run of levels, e.g. "First Week At Work" in January.

**All quests are additive.** There is no penalty state anywhere in the quest system.

---

## 8. The mascot

The brief asks for an evaluation rather than a pick. Here is the evaluation.

### 8.1 Criteria

| Criterion | Why it matters here |
|---|---|
| **Voice metaphor** | The product is about finding your voice. A mascot that has nothing to do with speech wastes the strongest available symbol |
| **Cultural fit (India)** | Primary market. A culturally foreign animal reads as an imported product |
| **Non-infantilising** | Learners include adults with intellectual disabilities who are routinely handed children's material. This is the highest-stakes criterion |
| **Silhouette at 24px** | Notification icons, tab bars, favicons |
| **Expression range without a face** | Birds cannot smile. Whatever is chosen must convey mood some other way |
| **Animation economy** | Every state costs illustration time |
| **No negative connotation** | For any disability community, any Indian region, any religion |

### 8.2 The candidates

**Honey badger.** Strength: fearlessness is a genuinely good metaphor for self-advocacy. Fatal
problems: it is famous for aggression, which is precisely the wrong model for workplace
communication ("be more like a honey badger" is bad advice in a performance review); it has no
voice association; and it is culturally an internet meme, not an Indian icon. **Rejected.**

**Swan.** Strength: elegant, calm, culturally significant in India (Hamsa, the vehicle of
Saraswati — goddess of speech and learning, which is *extremely* on-brand). Problems: swans are
mute in popular association ("swan song" is about dying); the mythological weight is high enough
that a cartoon version risks offence; and the silhouette at 24px is a white blob. **Rejected, with
regret** — the Saraswati link is the best conceptual fit of any candidate.

**Kingfisher.** Strength: spectacular colour, sharp silhouette, common across India, and
associated with *precision* and *patience* — it waits and then acts decisively, which is a lovely
metaphor for waiting for your moment in a conversation. Problems: strongly associated with a beer
brand and a defunct airline in India, which is a brand-collision an accessibility product cannot
afford; and it is a solitary hunter, which is the wrong social metaphor. **Rejected on brand
collision alone.**

**Elephant.** Strength: enormously loved in India, associated with memory (good for spaced
repetition), wisdom, and Ganesha (remover of obstacles — thematically excellent). Problems:
Ganesha association makes a cartoon elephant religiously sensitive; "elephant in the room" is a
communication-avoidance idiom, which is unfortunate; large body is hard to animate expressively in
a small space; and it has no voice association. **Rejected.**

**Parrot.** Strength: the definitive talking bird, culturally ubiquitous in India, brilliant
silhouette, huge expression range via crest and head angle. Fatal problem: **parrots mimic without
understanding.** For a communication-learning product aimed at people who are routinely accused of
"just repeating" or "parroting" — a slur genuinely used against autistic people who echo, and
against AAC users — this is the single worst possible symbol. **Rejected, decisively.**

**Mynah.** Strength: the common mynah is everywhere in urban India, familiar to every learner
without being sacred. It is famous for *learning* to speak rather than mimicking — the distinction
matters and is well understood colloquially. It is a bold, social, adaptable bird that thrives in
human environments, which is thematically exact for workplace integration. Strong silhouette: the
yellow eye patch is unmistakable at any size and gives a distinctive monochrome mark. It is not
sacred, so a cartoon is safe. It is not a brand. Expression range through crest, head angle and
eye position is sufficient. **Selected.**

### 8.3 Mitra

**Name.** Mitra — Sanskrit and Hindi for *friend*. Pronounceable across Indian languages, two
syllables, no negative homophone in the target languages. Gender-neutral.

**Backstory.** Mitra is a common mynah who works in the same building as the learner. Not a
teacher, not a coach, not a therapist — **a colleague who has been there a bit longer.** That
framing is the entire personality specification, and it is what keeps Mitra from becoming
patronising. A colleague tells you where the good chai is and what the manager is like. A colleague
does not congratulate you for showing up.

**Personality rules:**

| Mitra does | Mitra never |
|---|---|
| Notice specific things ("that one took three goes and you got it") | Praise effort alone ("well done for trying!") |
| Share a tip like a peer | Instruct like a teacher |
| Be pleased | Be proud *of* you |
| Wait | Hurry you |
| Be absent during a mission | Interrupt |

**Emotional states — five, and no sixth:**

`calm` (default, resting) · `delighted` (something went well) · `listening` (during recording,
head tilted) · `thinking` (working something out — **the most concerned Mitra ever looks**) ·
`greeting` (used once, on welcome).

**There is no sad, disappointed, crying or worried state, and there never will be.** A mascot that
looks let down turns a bad day into a small shaming. This is a hard constraint, not a style
preference.

**Growth.** Mitra does not level up, gain accessories automatically, or "get stronger as you do" —
that mechanic implies the mascot's wellbeing depends on the learner's performance, which is
emotional leverage. Mitra's *outfits* are cosmetic unlockables the learner chooses. Mitra is the
same bird on day 1 and day 200.

**Accessibility contract:**

- `aria-hidden` by default. Mitra is decoration; the message is in the text beside the bird.
- Never the sole carrier of any information.
- Every animation plays **once**. No idle loop — a permanently moving character is a permanent
  distraction on a screen somebody with an attention difficulty is trying to read.
- Respects reduced motion completely.
- Absent during missions.

**Voice.** Text only at launch. If voice is added: warm, unhurried, adult, regionally Indian-
English, and **never** the bright over-enunciated register used with children.

**Notifications.** Specific and forward-looking. "World 3 has a phone call waiting" — never "You
haven't practised in 3 days", never a streak warning, never guilt.

---

## 9. Design system

### 9.1 Principles

1. **Accessible by default, not by option.** The AAA path is the default path.
2. **Colour never carries meaning alone.** Every state has a second signal.
3. **Nothing is smaller than 44px, and the learner can make it 88px.**
4. **Every component works at 400% zoom** without horizontal scroll.
5. **Every component works with no colour** (forced-colours mode).

### 9.2 Colour

Four base themes exist and are verified by test: light/dark × standard/high-contrast. The redesign
adds ten world palettes (already built, all AAA verified).

**New:** a semantic layer so components never reference a raw token —
`--surface-raised`, `--surface-sunken`, `--text-primary`, `--text-secondary`,
`--interactive-rest/hover/press`, `--focus-ring`, `--success-ink`, `--attention-ink`.

**Rule:** no component may use a world palette for anything except world identity. A world colour
leaking into a button breaks the map's meaning.

### 9.3 Typography

Base is 18px, not 16px — Easy-Read requires ≥18px and there is no reason to make everyone else
squint for convention. Scale: 1rem / 1.125 / 1.375 / 1.75 / 2.25. Line height 1.6 body, 1.35
headings, 1.8 Easy-Read.

**Add:** a `<Text>` primitive with a `variant` prop, so type is never set inline. Easy-Read mode
switches variant mapping globally rather than each screen branching.

### 9.4 Spacing, elevation, shape

Spacing scale exists (xs → xl). **Add:** a `<Stack>` primitive so spacing is never a magic number
in a style object.

Elevation: four levels, expressed as border + subtle shadow. **Shadow is never the only signal for
elevation** — it disappears in high contrast. Border weight carries it.

Radius: 4 / 8 / 14 / 18 / 999.

### 9.5 The `ui/` primitive layer — F1

The single highest-priority engineering task.

```
ui/
  Button.tsx        variants: primary secondary quiet danger · sizes · loading · icon
  Card.tsx          elevation, interactive/static, world-tinted variant
  Stack.tsx         vertical/horizontal, gap from scale, wrap
  Text.tsx          variant, tone, easy-read aware
  ProgressDots.tsx  mission progress — the "end is visible" component
  ProgressBar.tsx   labelled, never colour-only
  Icon.tsx          one sprite, consistent sizing, decorative by default
  Sheet.tsx         bottom sheet, focus trap, restore
  Dialog.tsx        Radix-backed, focus managed
  Skeleton.tsx      respects reduced motion (no shimmer when reduced)
  Field.tsx         label + error + hint, always associated
  Announce.tsx      declarative aria-live
```

**Migration strategy:** build primitives with tests, then migrate one screen per PR. Tests for
each screen stay unchanged — if a screen's tests still pass after migration, the refactor is
correct by construction. No feature flag needed; this is behaviour-preserving.

### 9.6 Illustration

A constrained SVG character system rather than commissioned raster art: eight workplace characters
built from a shared skeleton with swappable head/expression/pose layers. Reasons: it scales, it
themes (works in dark and high contrast), it costs nothing per additional expression, and it can
be authored by an engineer once a designer defines the parts.

---

## 10. Motion

### 10.1 The rule that makes motion safe

**Animation may only emphasise something already true in the DOM.** Remove every animation and the
app must be completely usable and say exactly the same things. That is testable and is tested.

### 10.2 Budget

| Token | ms | Use |
|---|---|---|
| `instant` | 90 | hover, press, focus |
| `quick` | 160 | tile state, tooltip |
| `base` | 240 | panel, route transition |
| `celebrate` | 420 | **ceiling anywhere in the product** |

**Why 420ms is the ceiling:** a learner using switch scanning waits out every animation before the
next scan step is safe to read. A 900ms celebration costs them real time on every item.

### 10.3 Three motion levels

| Level | Behaviour |
|---|---|
| **Full** | Everything. Bounded particle burst on major wins |
| **Gentle** *(default)* | Transforms and fades; no particles, no parallax |
| **Still** | Opacity only |

`prefers-reduced-motion: reduce` forces **Still** unless the learner has explicitly chosen
otherwise in-app. The OS is a default, not a verdict — someone who set reduced motion for a
different app must be able to turn animation back on here.

### 10.4 Reduced motion keeps cross-fades

Reduced mode returns a short opacity transition, **not `none`**. A hard cut loses the signal that
something changed, and that signal is doing real work for a learner with a cognitive disability.
The change simply must not travel through space.

### 10.5 Celebration

The payoff moment, and the one place 420ms is justified.

**Sequence:** stars land one after another (130ms stagger — counting up, not a state change) →
XP counts up → Mitra reacts → badge if earned → "One more" / "Done for today".

**Announced once, as a complete sentence.** Not five separate `aria-live` interruptions — a screen
reader user should hear "Level finished. Two stars. Forty XP." as one utterance, after the
animation, not during it.

**Particles: Full level only, ≤24, single emission, no loop, no full-screen coverage.**

### 10.6 Performance

60fps means `transform` and `opacity` only. No animating `width`, `height`, `top`, `left`,
`box-shadow`. `will-change` applied only during an animation and removed after. Target device is a
₹8,000 Android, not a MacBook.

---

## 11. Responsive

| Breakpoint | Layout |
|---|---|
| ≤479 (phone) | Single column, bottom nav, full-bleed missions |
| 480–899 (large phone/small tablet) | Single column, wider gutters |
| 900–1199 (tablet) | Two-column map, side nav |
| ≥1200 (desktop) | Two-column with persistent nav, content capped at 80rem |

**Zoom is a first-class breakpoint.** At 400% a 1280px viewport behaves as 320px. Every layout is
tested at 400%; horizontal scroll is a failure.

Missions are **always** single-column regardless of viewport. A mission is one thing.

---

## 12. Disability-first personalisation

**The most important section in this document.**

### 12.1 The architectural stance

There is a real tension between the brief and the codebase, and resolving it correctly matters
more than any visual decision.

**The brief says:** the learner picks a disability profile and gets an entirely different
experience.

**The codebase says (ADR-0001):** the runtime mechanism is *channels* — what you can use to
receive and produce — not *conditions*. This is deliberate and it is right, for three reasons:
two people with the same diagnosis need different things; many learners have several conditions or
none diagnosed; and asking a disabled person to name their condition to use a product is a barrier
in itself.

**The resolution — and it satisfies both fully:**

> A **learning profile is a preset**, not a record. Choosing one configures channels, mission mix,
> pacing, coaching strategies and scoring weights in a single action. It is never stored as a
> diagnosis, never required, always overridable setting-by-setting, and "I would rather not say"
> is the first option in the list and a complete answer.

The learner gets the "built for me" experience the brief demands. The system stores capabilities,
not conditions. Nobody is asked to prove or name anything.

### 12.2 Sixteen profiles

Thirteen exist. Three are added:

| Profile | Primary adaptation |
|---|---|
| Prefer not to say | Widest compatibility, nothing assumed |
| Deaf / hard of hearing | Captions + ISL; nothing depends on hearing |
| Non-speaking | Symbols and typing; **no activity ever requires voice** |
| Stammer | Never timed, fluency near-zero weight, SLP strategies |
| Blind | Audio-first, screen-reader-shaped, drag missions down-weighted |
| Low vision | High contrast, 64px targets, audio alongside |
| Autistic | Literal wording, rules stated, context missions up-weighted |
| Intellectual disability | One thing per screen, pictures, difficulty ceiling that lifts |
| Dyslexia | Audio with every text, no walls of words |
| Aphasia | Recognition weighted highest, never rushed, symbol always available |
| Stroke recovery | Short sessions, shortened baseline window |
| Cerebral palsy | 72px targets, switch-ready, pace weighted zero |
| Communication anxiety | Graded exposure, roleplay weighted highest, visible exit |
| **ADHD** *(new)* | Shortest sessions, distraction-free mission chrome, movement between missions, novelty weighted, quests emphasised |
| **Selective mutism** *(new)* | **Speech never requested and never framed as avoidance.** Text/AAC first. Roleplay via text. Progression identical |
| **Speech delay** *(new)* | Modelling-first: hear/see it before producing. Recognition before production. Extended production time |

### 12.3 What a profile actually changes

Nine axes. A preset that changed only labels would not be worth having.

| Axis | Example: non-speaking vs stammer |
|---|---|
| **Input channels** | `aac,text,switch` vs `speech,text` |
| **Output channels** | `captioned_text,pictograph` vs `captioned_text,audio` |
| **Presentation** | 56px targets vs 44px |
| **Session length** | 8 min (AAC composition is genuinely slower) vs 6 min |
| **Mission mix** | `choose_in_context` ×1.3 vs `roleplay` ×1.3 |
| **Difficulty** | start 2 vs start 2 |
| **Scoring weights** | pronunciation **0.0** vs 0.15; fluency 0.0 vs 0.05 |
| **Strategies** | compose-ahead, phrase-bank shortcut vs easy onset, light contact |
| **AI register** | never asks to speak vs never comments on fluency |

**The build refuses any preset that removes a world.** Reordering and re-weighting only. Deciding
somebody cannot learn interviews because of their disability is the exact harm this product
exists to refuse.

### 12.4 Profile → mission mix

Mission weights bias selection; they never eliminate a type. Rationale for the three least
obvious:

- **Aphasia weights `recognise` highest of any profile (1.6).** Recognition is reliably preserved
  when retrieval is not, so a session that opens with recognition opens with a success — and
  word-finding recovers faster from confidence than from drilling.
- **Communication anxiety weights `roleplay` highest (1.4).** This looks backwards until you
  notice that avoidance is the maintaining factor in communication anxiety, and graded rehearsal
  in a consequence-free place is the intervention.
- **Autism weights `choose_in_context` and `scenario` at 1.4.** The gap is rarely vocabulary — it
  is which of several correct-sounding phrases the room expects, which is exactly what those drill.

### 12.5 Profile → AI

Composed system-prompt fragments, each hashed and versioned so a generation stays interpretable:

```
base_workplace_colleague
  + profile_fragment(non_speaking)   "Never ask the learner to speak or read aloud.
                                      Never comment on speed of reply."
  + strategy_fragment(compose_ahead)
  + register_fragment(easy_read)
```

**Prompt sprawl is the risk.** Mitigation: fragments are data, composition is one function, every
composition is hashed, and the fixture suite runs the condescension filter against **every profile
× every scenario** rather than a sample.

### 12.6 Onboarding

Four stages. Stage 0 and 1 exist and work; 2 and 3 are extended.

- **Stage 0 — Zero input.** Read `prefers-reduced-motion`, `prefers-contrast`,
  `prefers-color-scheme`, pointer type, viewport. Apply immediately, before first paint.
- **Stage 1 — The four-door screen.** Four huge self-narrating targets, each simultaneously
  labelled in text, pictograph, audio and ISL. Reachable by tap, keyboard, switch and voice.
  **This screen remains the hardest UI in the product.** It exists and works.
- **Stage 2 — Profile.** *New.* "Does one of these sound like you?" Sixteen cards, plain language,
  Easy-Read label, and what choosing it changes stated **before** committing. "I would rather not
  say" is first. Skippable.
- **Stage 3 — Confirmation, in the chosen channel.** Pace, captions, session length, goals — asked
  through the channel Stage 1 established.
- **Stage 4 — Speech enrolment.** Only if they will use voice. Skippable, resumable, never a wall.

**Constraint: the first mission must be reachable within 90 seconds** including all of the above.
Onboarding that outlasts the first win loses the learner before the product has shown them
anything.

### 12.7 Changing your mind

From Settings, in ≤2 actions, from anywhere — an existing charter requirement. Changing a profile
**re-presets** rather than overwrites: individual settings the learner has personally changed are
preserved, and they are told which. Silently discarding a learner's own adjustments because they
tried a different preset would be a small betrayal.

---

## 13. Social stories, redesigned

### 13.1 What exists and why it must change

Six preset situations, 6–10 authored panels validated against the Carol Gray sentence-type ratio,
rendered through the modality router. The structural validation is genuinely good and stays.

But it is **linear**. The learner reads. Nothing they do changes anything. The brief is right that
this is the weakest experience in the product.

### 13.2 The redesign

**A scene graph, not a slide deck.**

```
Scene
  ├── setting          where, illustrated
  ├── characters[]     who is present, with authored expression
  ├── beats[]          lines of dialogue / narration (ContentBlocks)
  ├── choice           2–4 responses, each a ContentBlock
  └── branches{}       choice → next scene + character state change
```

**Every beat and every choice is a `ContentBlock`.** That is what makes a branching story work in
five modalities without forking: the choice arrives as speech for one learner, as three tappable
symbols for another, as ISL for a third. The existing router does all of it.

### 13.3 Consequence design

The critical design decision: **what happens after a poor choice.**

**Never:** "Wrong. Try again." · a game-over · a score · locking the branch.

**Always:** the story *continues*, and the consequence is *realistic and recoverable*. The
colleague looks confused. The supervisor asks again. Then — crucially — **the learner gets another
turn in the same conversation**, which is how real workplaces work and is the actual skill being
taught: recovery, not perfection.

**Mitra never comments during a story.** Reflection comes at the end, and it names what the branch
did rather than what the learner got wrong.

### 13.4 Endings

Three per story: **smooth**, **bumpy but recovered**, **unresolved**. All three are complete
endings; none is a failure. "Unresolved" is explicitly framed as a normal workplace outcome — some
conversations do not resolve, and a learner who believes every conversation must end well is badly
prepared.

Replay is encouraged and is a *courage* quest. The story remembers which endings have been seen.

### 13.5 Fourteen stories

Joining the office · Meeting coworkers · Lunch conversation · Asking for help · Receiving
criticism · Giving feedback · Presenting an idea · A customer interaction · An emergency ·
Asking for an adjustment ★ · Disclosure ★ · A performance review · Remote work · A conflict.

★ = sensitive. Explicit exit and a route to a human on every screen.

### 13.6 Character expression

Authored per branch as data — `{character, expression, intensity}` — rendered by swapping SVG
layers. **This is authored emotion, not detected emotion.** It teaches the learner to read a face
without ever analysing theirs, which is the §2.1 resolution made concrete.

---

## 14. Reward and motivation

### 14.1 The four legitimate currencies

| Currency | Earned by | Spent on | Rule |
|---|---|---|---|
| **XP** | Effort — attempting, per mission effort weight | Nothing. Level and tier only | **Never depends on correctness** |
| **Stars** | Mastery — coverage, accuracy, retention | Nothing. Recognition only | Third star needs *returning* |
| **Coins** | Milestones, quests | **Cosmetics only** | **Never gates content** |
| **Streak days** | Practising on a day | Nothing | **Only ever goes up** |

### 14.2 XP is for effort

`award_xp` **cannot see correctness** — enforcement by function signature. A learner who attempts a
hard phrase and gets it wrong earns the same as one who got it right. Two reasons: effort is the
behaviour that produces learning, and scoring correctness twice (FSRS + XP) doubles the penalty for
a bad day.

Stretch bonus for attempting above level — **for attempting, not succeeding.**

### 14.3 Streaks that cannot punish

- Count **days practised**, which only increases.
- Current run tracked and celebrated; **its loss is never announced**, never shown falling, never
  framed as at risk.
- Freeze tokens accrue automatically from use — earned by using the product, never bought.
- On a break, `longest` survives permanently. **You never lose what you did.**
- **`days_until_streak_at_risk()` exists and deliberately returns `None`**, with a comment
  explaining that it is the function the next person will reach for when asked for a "your streak
  ends tomorrow!" notification, and that it is loss aversion and will not be built.

### 14.4 Badges

Four families: **consistency**, **mastery**, **courage** (attempted something hard, practised
disclosure), **growth** (beat your own baseline). Courage badges reward the *attempt*.

Every badge carries a text label and an announcement. Badge art alone excludes P1.

The full catalogue is visible from day one — **hidden goals are a dark pattern; visible ones are a
map.**

### 14.5 Avatar and cosmetics

Learner avatar plus Mitra outfits, bought with coins. Deliberately shallow: a deep cosmetic
economy competes with learning for attention, and a learner grinding for coins is a learner not
practising.

**Avatar must include** wheelchairs, hearing aids, cochlear implants, white canes, AAC devices,
prosthetics and guide dogs as **ordinary options presented alongside hats and shirts** — not in a
"disability" category, not as a special section. That framing is the whole point.

### 14.6 What is never built

No leaderboards. No leagues. No hearts, lives or energy. No loss aversion. No public comparison.
No shame states. No timers.

---

## 15. Multilingual

### 15.1 Four independent tiers

Restating §2.11 as architecture, because conflating these is the single most expensive mistake
available here.

**Tier 1 — UI strings.** ~600 strings, standard i18n, all 12 languages. Cost: low.
**Tier 2 — AI explanation.** A locale parameter in the prompt. All 12. Cost: near zero.
**Tier 3 — Phrase bank.** 226 phrases *culturally adapted*, not translated — workplace idiom does
not survive literal translation. Needs a native speaker per language. Cost: high. **English +
Tamil + Hindi by pilot.**
**Tier 4 — Speech analysis.** G2P, phoneme inventory and acoustic model per language. A research
project each. **English only, stated plainly in the UI.**

### 15.2 Architecture

- Locale is on the CAP (`primary_language` exists, currently constrained to three).
- **Learning language and interface language are separate fields.** A learner may want a Tamil
  interface while practising English workplace phrases — that is the most common real case in the
  target market, and collapsing them into one setting breaks it.
- `ContentBlock.representations` gains per-locale variants; the router already selects
  representations, so this needs no new rendering logic.
- Bundles are lazy-loaded per locale — nobody downloads twelve languages.
- **RTL (Arabic) is a layout property, not a translation property.** Logical CSS properties
  (`margin-inline-start`, not `margin-left`) from the start. Retrofitting RTL is expensive;
  starting with logical properties is free.

### 15.3 Honesty requirement

When a learner selects a language where Tier 3 or 4 is unavailable, **say so in the UI, in that
language, before they start.** A learner told plainly will accept it. A learner who discovers it by
having their Tamil pronunciation scored as bad English will leave and will be right to.

---

## 16. AI system review

| Module | State | Change |
|---|---|---|
| **ASR** | Whisper + vocabulary biasing | Wire biasing into every mission with a known target |
| **Forced alignment / GOP** | Complete, needs `requirements-ml.txt` | Surface *only* into PPI, never raw |
| **Prosody** | Complete, deterministic | Surface as coaching cues in level outro |
| **Disfluency** | Interface complete, **weights missing** | Train on SEP-28k. Honour the precision floor already implemented |
| **PPI** | Complete + 2 fairness gates | Chart it with the baseline drawn — the emotional payoff screen |
| **Personalised ASR** | Biasing live; LoRA blocked | **Request UASpeech access this week** |
| **RAG** | Brute-force over 226, keyword fallback | Fine at this scale. Revisit only if the corpus 10×s |
| **Role-play** | Guardrailed, ZPD adaptation | Becomes a mission type |
| **Guardrails** | Six checks incl. condescension | Extend condescension fixtures to every new profile |
| **Rubric** | 4-layer enforcement, invariance gate | Unchanged. This is finished work |
| **Recommender** | Rule-based, explainable | Extend to recommend *levels*, not just phrases |
| **Emotion detection** | Not built | **Do not build.** See §2.1 |
| **Confidence estimation** | Self-report | Keep self-report. See §2.2 |
| **Forecasting** | Not built | **Do not build a ceiling.** See §2.8 |

**One integration principle:** the AI's job is to make the *next thing* better, never to produce a
verdict about the learner. Every AI output should be actionable by the learner within one session.

---

## 17. Implementation plan

Eight phases. Each is independently shippable and independently revertable.

---

### Phase 0 — Unblock the long leads (Week 0, parallel to everything)

Zero engineering. Do it this week because everything else can proceed in parallel and these
have multi-week latency.

| Action | Latency | Blocks |
|---|---|---|
| Request **UASpeech** + Speech Accessibility Project access | 2–4 weeks | M8 LoRA |
| Contact **Deaf signer / ISL interpreter** | Weeks–months | 100 ISL clips, WCAG 1.2.6 |
| Approach 3–4 **pilot institutions** | Months | M18 pilot |
| Brief an **illustrator** for Mitra + 8 characters | 2–4 weeks | Phase 4, 5 |
| Run **TTS bootstrap** for 452 audio files | 1 day | The audio channel |

**The TTS bootstrap is the highest value-per-hour task in this entire document.** Two personas
currently depend on a channel that has zero assets.

---

### Phase 1 — Foundation (3 weeks)

**Objective:** make the redesign possible. Nothing user-visible changes.

**Files:** new `apps/web/src/ui/**`; `apps/web/src/routes/**`; `packages/platform/samvaad_platform/flags.py`.

**Architecture:** primitive layer beneath features; accessible route wrapper; route-level code
splitting.

**Frontend:** the twelve primitives in §9.5. `<AppRoute>` wrapper handling focus, announcement and
title on every navigation. React Router with lazy routes.

**Backend:** none. **Database:** none. **API:** none.

**Accessibility:** the route wrapper is the highest-risk item — a client router that does not move
focus is a serious regression from today's tab bar. Test: every route change moves focus to
`<main>`, announces, and updates title.

**Testing:** primitive unit tests + axe per primitive; route-change a11y test; **all 267 existing
web tests must still pass unchanged.**

**Performance:** initial JS ≤120KB gzipped; Lighthouse performance ≥90 on throttled 4G.

**Deployment:** behind no flag — behaviour-preserving.
**Rollback:** revert; nothing else depends on it yet.
**Migration:** none.

**Acceptance:** 0 inline `style={{ }}` in migrated screens · every route accessible · bundle
budget met · existing tests green.

---

### Phase 2 — The loop (4 weeks)

**Objective:** the game loop exists end to end. **This is the phase where the product stops being
a dashboard.**

**Files:** `apps/web/src/game/**`; `apps/api/app/routers/missions.py`;
`apps/api/app/learning/missions.py`; `packages/content/curriculum/missions.json`;
`packages/contracts/schemas/lesson-mission.schema.json`.

**Architecture:** mission specification in contracts; mission selection server-side (profile-aware);
level runner client-side; celebration as a shared component.

**Database:** `level_attempts` (level_id, user_id, started_at, finished_at, missions_completed).
Additive. Alembic **required** — see X2.

**API:** `GET /missions/level/:id` (profile-weighted mission set) · `POST /missions/:id/answer` ·
`POST /levels/:id/complete`.

**Frontend:** world map as home · level intro · runner · three mission types (Match it, What fits
here, Say it your way) · celebration.

**Animations:** stars land, XP counts, Mitra reacts. Three motion levels.

**Accessibility:** every mission answerable in every channel the profile offers — enforced by a
shared harness that runs each mission type × each input adapter. No timers anywhere.

**Testing:** mission harness (types × adapters) · celebration announces once as one sentence ·
persona walkthrough extended to the level runner · axe on runner and celebration.

**Performance:** mission transition ≤240ms · no layout shift between missions.

**Deployment:** flag `game_loop`, staff → 10% → 100%.
**Rollback:** flag off restores the tab bar. Keep the old shell for one release.
**Migration:** none — progress derives from existing cards.

**Acceptance:** a learner completes a level in all five modalities · celebration fires · stars
persist · zero critical axe · persona suite green.

---

### Phase 3 — Personalisation (3 weeks)

**Objective:** the profile genuinely changes the experience.

**Files:** `features/onboarding/ProfileChooser.tsx`; `app/learning/personalise.py`;
`services/genai/prompts/fragments/**`; `curriculum/profiles.json` (+3 profiles).

**Database:** `communication_ability_profiles.learning_profile_id` (nullable),
`motion_preference`, `celebration_level`. All additive.

**API:** `GET /journey/profiles` (exists) · `PUT /profile` accepts a preset · mission selection
consumes weights.

**Frontend:** profile chooser in onboarding · settings change flow · profile-aware mission mix.

**Accessibility:** the chooser is the second-hardest screen after the four-door. Sixteen options
must be scannable, switch-navigable, and readable in Easy-Read. **What each preset changes is shown
before committing.**

**Testing:** per-profile snapshot of the resulting configuration · condescension fixtures run
against **every profile × every scenario** · a test that no preset can remove a world.

**Deployment:** flag `learning_profiles`.
**Rollback:** flag off → everyone gets `prefer_not_to_say` behaviour, which is the current
behaviour. Safe.
**Migration:** existing learners get `learning_profile_id = NULL`, behaving exactly as today.

**Acceptance:** two profiles produce measurably different mission mixes, prompts and weights ·
change flow ≤2 actions · no profile removes content.

---

### Phase 4 — Character and craft (3 weeks)

**Objective:** it looks and feels like a product somebody made on purpose.

**Files:** `apps/web/src/illustration/**`, `game/Mitra.tsx`, `styles/**`.

**Frontend:** Mitra's five states with real illustration · world map polish · empty/loading/error
states for every surface · skeletons · full dark mode pass · sound design (off by default).

**Animations:** page transitions · micro-interactions · Mitra reactions · celebration polish ·
three motion levels wired to settings.

**Accessibility:** Mitra `aria-hidden` throughout · every animation removable with no information
loss · reduced motion honoured at both OS and app level · forced-colours pass.

**Testing:** visual regression on key screens · a test that asserts the app is fully usable with
all animation disabled · axe across every new surface.

**Performance:** 60fps on a mid-range Android — profiled, not assumed · `transform`/`opacity` only.

**Deployment:** flag `motion_v2`.
**Rollback:** flag off → Still level everywhere.

**Acceptance:** 60fps profiled on target hardware · no animation carries meaning · dark mode
complete · zero critical axe.

---

### Phase 5 — Stories (4 weeks)

**Objective:** stories become interactive adventures.

**Files:** `apps/web/src/story/**`; `services/genai/stories/**`;
`packages/content/stories/**`; `app/routers/stories.py`.

**Database:** `story_runs` (user_id, story_id, path[], ending, completed_at). Additive.

**API:** `GET /stories` · `POST /stories/:id/start` · `POST /stories/:id/choose` ·
`GET /stories/:id/endings`.

**Frontend:** scene renderer · character layer system · choice UI **through the modality router** ·
ending screen · replay.

**Accessibility:** every beat and choice is a `ContentBlock` — so the whole story works in five
modalities with no forking. Sensitive stories carry an exit and a route to a person on every
screen.

**Testing:** every branch reachable · every choice answerable in every channel · no branch is a
dead end · sensitive stories always show the exit.

**Deployment:** flag `stories_v2`, alongside the existing linear stories.
**Rollback:** flag off restores linear stories, which keep working.
**Migration:** existing stories remain readable.

**Acceptance:** 14 stories, 3 endings each, all branches reachable in all five modalities.

---

### Phase 6 — Rewards and quests (2 weeks)

**Objective:** reasons to return that are not guilt.

**Files:** `app/learning/rewards.py`, `app/routers/rewards.py`, `apps/web/src/rewards/**`.

**Database:** `coin_ledger`, `unlocks`, `quest_progress`. Additive.

**API:** `GET /rewards/me` · `POST /rewards/unlock` · `GET /quests`.

**Frontend:** coin display · shop · avatar builder · quest panel · daily goal ring.

**Accessibility:** avatar builder must include mobility and communication aids **as ordinary
options alongside hats**, never in a separate category.

**Testing:** no unlock gates content · no quest has a penalty state · streak never announces loss.

**Deployment:** flag `rewards`.
**Rollback:** flag off; coins retained in ledger, simply not shown.

**Acceptance:** cosmetics only · daily goal derives from the learner's own session length · zero
loss-aversion copy (asserted by test).

---

### Phase 7 — Multilingual (4 weeks)

**Objective:** Tiers 1 and 2 in all twelve; Tier 3 in three.

**Files:** `apps/web/src/i18n/**`, `packages/content/locales/**`, prompt locale parameter.

**Database:** `users.interface_locale` separate from `learning_locale`.

**API:** `Accept-Language` honoured; `GET /content?locale=`.

**Frontend:** locale switcher · lazy bundles · RTL via logical properties · **honest capability
notice** when Tier 3/4 is unavailable.

**Accessibility:** `lang` attribute correct per element — a screen reader reading Tamil with an
English voice is unusable. Mixed-language content must mark spans.

**Testing:** every UI string externalised (no hard-coded English) · RTL layout test · `lang`
correctness test.

**Deployment:** per-locale flags.
**Rollback:** per-locale.

**Acceptance:** 12 UI locales · 12 AI explanation locales · 3 phrase-bank locales · RTL correct ·
capability limits stated in-language.

---

### Phase 8 — Hardening and pilot (4 weeks + ongoing)

**Objective:** the claims become evidence.

**Work:** manual screen-reader passes (NVDA, VoiceOver, TalkBack) on the top 10 flows · switch-
access pass with a real device · 400% zoom pass · voice-control pass · cognitive-load review by a
special educator · Alembic migrations · Postgres RLS · Sentry + PostHog · load test · runbooks ·
backup restore test · WCAG 2.2 conformance statement published with the §2.10 exceptions named.

**Acceptance:** zero critical/serious axe across every route × every modality · three screen
readers pass · persona suite green · Lighthouse a11y ≥95 · pilot cohort running.

---

### 17.1 Sequencing rationale

Foundation before loop, because the loop cannot be built well on inline styles. Loop before
personalisation, because there must be something to personalise. Personalisation before craft,
because the craft must be tested against the profiles it serves. Stories after craft, because
stories need the character system. Rewards late, because they are the least essential and the most
tempting to over-build. Multilingual late, because it multiplies the cost of everything before it.

**Total: ~27 weeks of engineering, plus Phase 0 running in parallel from week 0.**

---

## 18. Testing, risk and rollback

### 18.1 The testing bar

Existing: 817 tests across seven CI jobs. **Nothing in this redesign may reduce that number.**

New suites required:

| Suite | Asserts |
|---|---|
| **Mission harness** | Every mission type × every input adapter is completable |
| **Motion removal** | App fully usable and semantically identical with all animation off |
| **Profile matrix** | Each profile produces a distinct, valid configuration |
| **Condescension × profile** | Every profile × every scenario passes the filter |
| **Story branch coverage** | Every branch reachable, no dead ends, every choice answerable in every channel |
| **No-loss-aversion** | No user-facing string in the reward system mentions losing anything |
| **Route accessibility** | Every route moves focus, announces, sets title |
| **Zoom reflow** | Every route at 400% with no horizontal scroll |
| **Bundle budget** | Initial JS ≤120KB gzipped |

### 18.2 Top risks

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | **Router regresses accessibility** | Med | **Critical** | One shared wrapper; a route not using it fails a test |
| R2 | **Redesign breaks the modality router** | Low | **Critical** | Do not touch it. Presentation sits above it |
| R3 | **Illustration becomes the critical path** | **High** | High | Constrained SVG system an engineer can extend; brief the illustrator in Phase 0 |
| R4 | **Gamification drifts into dark patterns** | Med | **Critical** | Every mechanic needs a test asserting its refusal. `days_until_streak_at_risk` is the template |
| R5 | **Profiles become stereotypes** | Med | **Critical** | Co-design with disabled users per profile. No profile ships unvalidated by someone it describes |
| R6 | **Multilingual under-estimated** | **High** | High | Four tiers costed separately; be honest in the UI |
| R7 | **ISL clips never arrive** | **High** | Med | Start outreach week 0; degrade to captions gracefully |
| R8 | **Performance on target hardware** | Med | High | Profile on a real ₹8,000 Android, not a simulator |
| R9 | **Scope: 27 weeks becomes 50** | **High** | High | Phases 1–3 are the thesis. 6–7 are cuttable |
| R10 | **Manual SR passes keep slipping** | **High** | High | axe catches ~30%. Schedule them in Phase 4, not Phase 8 |

**R10 deserves emphasis.** The product's central claim is accessibility, and no screen reader has
ever been run against it. That is the largest gap between claim and evidence in the repository.

### 18.3 Rollback

Every phase ships behind a flag and every flag has a defined off-state that is the *current*
behaviour, not a broken one. The old tab shell is retained for one release after Phase 2.

**No phase deletes data.** Every schema change is additive. A rollback loses features, never
learner progress.

### 18.4 Definition of done

Unchanged from the execution plan, plus four:

- [ ] Works for all five personas, verified by the walkthrough suite
- [ ] Zero critical/serious axe violations
- [ ] Keyboard, screen-reader and switch-scan paths verified
- [ ] Works offline or degrades with an accessible message
- [ ] Loading, empty, error and offline states designed
- [ ] Copy reviewed for dignity
- [ ] Documented, with an ADR if a decision was made
- [ ] **Fully usable with all animation disabled**
- [ ] **Answerable in every input channel the profile offers**
- [ ] **No mechanic that punishes an absence**
- [ ] **Reflows at 400% zoom with no horizontal scroll**

---

## 19. What success looks like

**Engineering:** 817 → ~1,100 tests. Zero critical axe across every route × modality. ≤120KB
initial JS. 60fps on a ₹8,000 Android. Lighthouse a11y ≥95.

**Product:** a learner reaches their first completed mission within 90 seconds of first open. The
session loop is 3–7 minutes with a visible end. Day-7 return is the metric that matters.

**The claim, made provable:** WCAG 2.2 AAA-minus-two-documented-exceptions, three screen readers
passed by hand, a fairness gate in CI, and an audit record for every score.

**The sentence to aim for**, from a disabled learner rather than a judge:

> "It didn't try to fix me. It just let me practise."

---

## Appendix A — Decisions requiring sign-off

| # | Decision | Recommendation |
|---|---|---|
| A1 | Emotion detection | Curriculum + self-report only; never measure the learner |
| A2 | Body language | Comprehension only; never score the learner's body |
| A3 | Confetti | Three levels; Gentle default; reduced-motion forces Still |
| A4 | Forecasting | Build "what next", never a predicted ceiling |
| A5 | Languages | 12 UI / 12 AI / 3 phrase bank / 1 speech — stated honestly in-product |
| A6 | Mascot | Mitra the mynah |
| A7 | World map | Vertical list; decorative path deferred to V2 |
| A8 | Channel comparison | Moves from learner nav to `/demo` |
| A9 | AAA | Target; publish 1.2.6 and 3.1.5 as documented partials |

## Appendix B — ADRs to write

ADR-0008 Learning profiles are presets, not diagnoses ·
ADR-0009 Emotion as curriculum, never as measurement ·
ADR-0010 The world map is a list ·
ADR-0011 Three motion levels ·
ADR-0012 Four-tier multilingual ·
ADR-0013 Cosmetic-only currency ·
ADR-0014 Client router and the accessible route contract

---

*End of blueprint. No code should be written against this until Appendix A is signed off.*

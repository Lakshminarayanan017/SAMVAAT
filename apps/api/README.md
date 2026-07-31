# apps/api — API gateway

**Modules M1, M4, M13, M17** · FastAPI · Python 3.10+

The single security boundary. Nothing else in the system talks to the database.
Also hosts the learning service (spaced repetition, recommendation, gamification) as an
internal module rather than a separate deployment — see
[ADR-0004](../../docs/ADR/0004-three-services-not-five.md).

---

## Run it

```bash
python -m venv .venv
.venv/Scripts/activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

Interactive API docs at `/docs`. No `.env` is needed — every setting has a
development default.

> Run `npm run contracts:build` from the repo root first. The API imports the
> generated Pydantic models and will refuse to start without them, with a message
> telling you exactly that.

```bash
pytest          # tests
ruff check .    # lint
```

---

## Layout

```
app/
├── main.py         application factory, middleware, lifespan
├── config.py       settings, with production-only validation
├── contracts.py    stable import path for the generated Pydantic models
├── routers/        one module per resource — the HTTP surface
├── learning/       FSRS, recommender, gamification (M4, M12, M13)
├── security/       consent enforcement, retention, RLS, audit log (M17)
└── models/         SQLAlchemy models (M1 onwards)
tests/
```

**Import rule:** `app/learning/` may not import from `app/routers/`. Learning logic is
pure and independently testable; the moment it reaches for a request object, splitting it
out later stops being a deployment change and becomes a rewrite.

---

## The practice loop (M4)

Two calls make the whole loop:

```
POST /practice/session   -> the phrases to practise now
POST /practice/review    -> record what happened, reschedule
```

**Scheduling** is [FSRS-4.5](app/learning/fsrs.py) — the published, openly specified algorithm,
not an invention of ours. SM-2 (the Anki default) systematically over-schedules easy material
and under-schedules hard material.

Nothing in the scheduling maths knows about disabilities, deliberately. The accessibility work
lives in **how a grade is derived**, not in the algorithm. Varying the maths per learner would
make progress incomparable and would quietly encode assumptions about who learns "slower".

### Grading without self-rating, and without timing

Every other spaced-repetition app asks the learner "how well did you know that?". We cannot:
many of our learners cannot reliably self-assess, and a self-rating button asks someone to judge
themselves several times a minute, forever.

So [`derive_grade`](app/learning/grading.py) reads observable behaviour instead — correctness,
attempts, hints. And it **cannot see response time**:

> `Attempt` has no duration field and `derive_grade` takes no timing argument. That is the
> enforcement, not a convention. A learner with dysarthria, a stammer or cerebral palsy responds
> slower *because of the disability* — feeding latency into the scheduler would re-teach material
> they already know, purely for being disabled, and it would look like a neutral algorithm doing
> it. Ethics **E6** and **E2**, with a test asserting no such field exists.

A transcription too uncertain to trust returns a neutral grade and records **no lapse**. An ASR
weakness must never surface as the learner's weakness.

### Session assembly

[`build_session`](app/learning/session.py) turns "what is due" into "what this session contains":

| Constraint | Why |
|---|---|
| Length is an **item count**, never a countdown | A countdown is a time-pressure mechanic (E6) |
| Slower input modes get **fewer items**, not a faster pace | AAC and switch scanning are slower — that is the modality, not the learner |
| Easy-Read profiles get a lighter session | One idea per screen limits how much a session may contain |
| At most **2 hard items**, and it opens on a likely win | A session that starts with four lapsed cards is one nobody comes back from |

The hard-item cap **outranks session length**: topping a short session up with lapsed cards
defeats the protection the cap exists for.

---

## Audio, consent and retention (M5)

```
POST   /audio/upload-url      -> an upload ticket, with a TTL and a plain-language notice
POST   /audio/consent         -> grant or revoke one purpose
GET    /audio/consent/{user}  -> what this learner has agreed to
POST   /audio/purge           -> run the retention job
DELETE /audio/user/{user}     -> erase a learner's audio
```

**The API never receives audio bytes.** The client uploads directly to object storage; this
service records only that an object exists and when it must be destroyed.

### Ethics E3, as code

> Raw audio is deleted within 24 hours of feature extraction, unless the learner has given
> separate, explicit, independently revocable consent to contribute to the research corpus.

Retention is a **TTL stamped at write time plus a job that enforces it** — not a sentence in a
policy, and not a promise someone has to remember. Every stored object carries a
[`RetentionReason`](app/security/retention.py); an object without one cannot be written.

| Reason | Lifetime | Requires |
|---|---|---|
| `processing` | **24 h**, hard ceiling | `speech_processing` |
| `learner_review` | 30 days | `store_audio_for_review` |
| `research_corpus` | While consent stands | `research_corpus` |

A test asserts the 24-hour constant directly, so raising it breaks the build rather than
quietly weakening the guarantee.

### Consent is enforced at the query layer

Not at the UI layer — a UI check is one forgotten conditional away from a silent leak.
[`require_consent`](app/security/consent.py) is called by the code that actually touches the
data, so forgetting is not possible.

Purposes are **separate and independently revocable**, because they are genuinely different
decisions: a learner may be happy for a trainer to hear a recording and entirely unwilling for
it to enter a research corpus. Collapsing those into one "I agree" is not consent.

**Revocation deletes immediately.** Consent you can withdraw without the data going with it is
a preference, not consent.

---

## Health endpoints

| Endpoint | Purpose | Checks dependencies? |
|---|---|---|
| `/healthz` | Liveness — the process is up | **No.** A liveness probe that checks dependencies takes the whole deployment down on a downstream blip. |
| `/readyz` | Readiness — it can serve traffic | Yes, and reports each dependency **separately**, so an incident tells you which thing broke. |

The speech service being down is *degraded*, not fatal: drills, role-play and every
non-speech modality keep working. That is the payoff of normalising all input modes to
`canonical_text` ([ADR-0002](../../docs/ADR/0002-canonical-text-response.md)).

---

## Ethics rules enforced here

| Rule | Where |
|---|---|
| **E3** — raw audio deleted within 24h | `config.audio_retention_hours` is capped at 24 by a Pydantic constraint, so a longer value fails at startup rather than quietly weakening the guarantee. Retention job lands in `security/retention.py` (M17). |
| **E5** — every AI score is human-overridable | `routers/feedback.py` (M14) |
| Consent enforcement | At the **query layer**, never the UI layer. `security/` (M17). |

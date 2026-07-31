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

# GenAI Service — M9, M10, M11

RAG-grounded role-play, social stories, and the bias-guarded interview rubric.

This is the one service with an external paid dependency and non-deterministic output. It is
separate for exactly that reason: it can be tested, rate-limited, budgeted, and swapped without
touching anything else (ADR-0004).

```
services/genai/
├── providers/     LLMProvider interface · Claude · a free-tier dev provider · scripted fallback
├── prompts/       Versioned, hash-tracked. Every generation records which prompt produced it.
├── retrieval/     RAG over the Workplace Language Bank
├── guardrails/    Schema · vocabulary · scope · safety · condescension · readability
├── roleplay/      M9  — scenario state machine, ZPD difficulty, scaffolding
├── stories/       M10 — Carol Gray structural constraint
├── rubric/      ★ M11 — the exclusion list, the scrubber, the audit record
├── eval/          The regression suite, including the disfluency-invariance gate
└── service/       FastAPI app
```

## The four rules this service is built around

**1. The LLM never speaks directly to a learner.** Every generation is a `ContentBlock`, and the
Modality Router renders it. That is what makes one generated turn become free-form conversation
for P1, a three-choice tap for P4, and captions plus ISL for P2 — one generation, five renderings.

**2. Nothing leaves without passing the guardrail chain.** Schema, vocabulary, scope, safety,
condescension, readability. A failure repairs once, then falls back to a scripted turn. A learner
never sees a guardrail failure; they see a slightly less interesting conversation.

**3. The rubric is architecturally blind, not instructed to be fair.** It receives a scrubbed
transcript with disfluencies removed, pauses collapsed and timing stripped. You cannot penalise
what you never received. See `rubric/README.md` and Ethics E2.

**4. The service works with no API key at all.** `ScriptedProvider` runs the whole product on
authored content. Development needs no key, CI needs no key, and an outage degrades to a working
experience rather than an error screen.

## Running it

```bash
cd services/genai
python -m venv .venv && .venv/Scripts/activate     # source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
uvicorn service.main:app --reload --port 8200
```

`ANTHROPIC_API_KEY` is optional. Without it the service starts, reports `provider: scripted`
through `/capabilities`, and every feature still works.

## Cost control

Four mechanisms, because one is never enough:

| Mechanism | Where | What it stops |
|---|---|---|
| Response cache | `providers/cache.py` | Paying twice for an identical context |
| Per-user daily token budget | `providers/budget.py` | One learner exhausting the month |
| Short constrained outputs | the response schemas | Paying for prose nobody reads |
| Cheap model for sub-calls | `providers/router.py` | Using a frontier model to classify an intent |

The spend cap on the API key itself is the fifth, and it is the only one that cannot be
bypassed by a bug in the other four.

# ADR-0004 · Three deployable services, not five

**Status:** Accepted
**Date:** 2026-07-31

## Context

The system has five logical concerns: the client, the API/CRUD layer, speech ML, generative AI,
and learning logic (spaced repetition, recommendation, gamification).

A microservice-per-concern layout is the reflexive choice. With a team of **two to three
people**, it is also a good way to spend the project's budget on deployment plumbing instead of
on the product.

## Decision

**Three deployables:**

| Deployable | Contains | Host |
|---|---|---|
| `apps/web` | React PWA — learner app and all dashboards | Cloudflare Pages |
| `apps/api` | API gateway **plus the learning service as an internal module** | Render / Fly.io |
| `services/speech` | ASR, alignment, GOP, prosody, disfluency, PPI | Hugging Face Spaces |

`services/genai` starts as a module inside `apps/api` and is **split out when** either LLM
latency starts blocking request threads, or it needs to scale independently. Its code lives in
its own top-level directory from day one so the split is a deployment change, not a refactor.

**Why speech is separate from day one:** PyTorch, Montreal Forced Aligner, and openSMILE make the
container multi-gigabyte with slow cold starts. Bundling that into the API would make every
CRUD request pay for it. It also has a completely different scaling profile — CPU-bound bursts
rather than steady I/O-bound traffic.

## Consequences

**Easy**
- Three CI pipelines, three sets of secrets, three dashboards to watch. A small team can hold
  this in their heads.
- Learning logic calls the database directly — no network hop, no distributed transaction, no
  eventual-consistency bug to debug at 2am.
- Each deployable maps to one free-tier host that suits its shape.

**Hard**
- `apps/api` becomes the largest codebase and needs internal discipline: `app/learning/` may not
  import from `app/routers/`, enforced by an import-linter rule.
- Splitting `genai` out later is real work, even with the directory pre-separated.

**Accepted cost:** a chunkier API service in exchange for far less operational surface.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Five microservices | Deployment and observability overhead a 2–3 person team cannot carry |
| A single monolith | The speech container's size and cold-start time would degrade every request |
| Serverless functions throughout | Cold starts are fatal for ML inference; free tiers are too constrained for PyTorch |

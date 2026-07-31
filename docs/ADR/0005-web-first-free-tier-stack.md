# ADR-0005 · React PWA first, on an all-free-tier stack

**Status:** Accepted
**Date:** 2026-07-31

## Context

The submitted abstract proposes Flutter for the client. Two constraints pushed against it:

1. The team is **two to three people over four to six months**, with no budget for
   infrastructure until a pilot is funded.
2. The trainer and institution dashboards are React regardless. Flutter for the learner app
   means maintaining two frontend stacks from week one.

Against that: the abstract's promise of *offline-first on entry-level Android* is a real
commitment to our users, not marketing, and it must survive this decision.

## Decision

**Build the learner app as an installable React PWA first. Port to Flutter as `[V2]`.**

The offline-first promise is kept through PWA capabilities rather than a native build:
service worker precaching, IndexedDB for profile/cards/sync-queue, and on-device ASR via
`onnxruntime-web` running a quantised Whisper model in WASM.

### The stack

| Layer | Choice | Why |
|---|---|---|
| Client | React 18 · TypeScript · Vite · Tailwind · **Radix primitives** | Radix gives correct focus management and ARIA for dialogs, menus and tabs. Hand-rolling these is the most common source of accessibility bugs. |
| Client host | Cloudflare Pages | Free, per-PR preview deploys |
| API | FastAPI, Python 3.10 | Same language as the ML side; Pydantic gives schema-first contracts that match our JSON Schema source of truth |
| API host | Render / Fly.io | Free allowance, Docker-native |
| Speech host | **Hugging Face Spaces** (Docker) | Free CPU with ~16GB RAM and persistent uptime — the best free home for CPU inference anywhere |
| Database | **Supabase** — Postgres + `pgvector` + Auth + Storage + row-level security | One free product covering five needs. The single biggest cost saving in the project. |
| Training | Google Colab / Kaggle | Training runs are episodic; a standing GPU is not needed |
| LLM | Claude API behind an `LLMProvider` interface | Provider-swappable; a free-tier model serves dev and fallback |
| Monorepo | **npm workspaces** | Built into npm 11. One less tool to install than pnpm, and adequate at this size. |

**Total infrastructure cost: zero.** Only LLM tokens cost money. A hard monthly spend cap is set
on the API key on day one.

## Consequences

**Easy**
- One frontend stack for the learner app and all three dashboards.
- Screen-reader and accessibility tooling on the web is far more mature than on Flutter — which
  matters more for this product than for almost any other.
- Demos instantly on any laptop, in any browser, with no install. This matters for pilot
  partners and for judges.
- Iteration is fast: hot reload, per-PR preview URLs.

**Hard**
- PWA install flow on iOS Safari is poor, and iOS restricts some background capability.
  Acceptable: our target users are overwhelmingly on Android.
- On-device ASR in WASM is slower than a native runtime. Mitigated by using Whisper `tiny`/`base`
  INT8 and treating offline transcription as provisional, with full analysis queued for reconnect.
- Free tiers sleep on idle. Cold starts of ~30s on the API host are tolerable in development and
  must be resolved before the pilot — the fix is one paid dyno, not an architecture change.
- We diverge from the submitted abstract and must be able to explain why. This ADR is that
  explanation.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Flutter first, as per the abstract | Two frontend stacks from week one; weaker accessibility tooling; slower iteration for a 2–3 person team |
| React Native | Inherits the two-stack problem without the web's accessibility maturity |
| Native Android | Excludes the dashboards entirely and cannot be demoed without a device |

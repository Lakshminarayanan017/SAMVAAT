# @samvaad/contracts

**Module M0** · The data contracts every other part of SAMVAAD depends on.

> Change anything here and you change the whole system. A contract change needs
> approval from all three tracks — see the contributing rules in the root README.

---

## Why this package exists

Two shapes carry the entire architecture. If you understand these, the rest of the
codebase follows.

### `ContentBlock` — content with no chosen rendering

A lesson is **data, not a screen**. A block holds a canonical meaning plus a bundle of
representations — native audio, slow audio, ISL clip, pictographs, Easy-Read paraphrase,
caption, phonemes — and the author **never picks one**. The Modality Router selects at
runtime from the learner's profile.

Consequence: a developer cannot forget to make a lesson accessible, because they never
decided how it renders. See [ADR-0001](../../docs/ADR/0001-modality-neutral-content.md).

### `LearnerResponse` — one shape for five input modes

Speaking, typing, signing, tapping symbols and switch-scanning all normalise to a
comparable `canonical_text`. One scoring engine, one scheduler, one recommender and one
dashboard therefore serve every disability profile, instead of five parallel
implementations of each. See [ADR-0002](../../docs/ADR/0002-canonical-text-response.md).

### `CommunicationAbilityProfile` — what the learner can actually use

Built during onboarding. Versioned, never updated in place, because progress data is only
comparable within a version. Read by the router, the scoring weights, the recommender and
every dashboard.

---

## Layout

```
contracts/
├── schemas/          ★ SOURCE OF TRUTH — JSON Schema draft-07
│   ├── common.schema.json                        enums and value objects
│   ├── content-block.schema.json
│   ├── learner-response.schema.json
│   └── communication-ability-profile.schema.json
├── generated/          committed output — never hand-edit
│   ├── types.ts        TypeScript, consumed by apps/web
│   └── models.py       Pydantic v2, consumed by apps/api and services/*
├── src/
│   ├── index.ts        public export surface
│   └── guards.ts       runtime behaviour a schema cannot express
├── fixtures/
│   ├── valid/          must validate AND satisfy every accessibility rule
│   ├── invalid/        must be REJECTED by schema validation
│   └── inaccessible/   schema-valid but must FAIL an accessibility rule
└── scripts/
```

---

## Commands

```bash
npm run contracts:build      # schemas → generated/types.ts + generated/models.py
npm run contracts:validate   # run all three validation passes
npm run contracts:check      # fail if generated code has drifted from the schemas
```

Generated code is committed so consumers do not need the toolchain to build. CI runs
`contracts:check` to keep that honest.

---

## The accessibility gate

`contracts:validate` runs three passes. The second is the one that matters.

| Pass | What it proves |
|---|---|
| **1 · Schema** | Blocks are well-formed. Fixtures in `invalid/` are correctly rejected. |
| **2 · Accessibility** | Every block is *reachable by all five personas*. This is the automated guarantee behind "accessibility as architecture". |
| **3 · Gate self-test** | Fixtures in `inaccessible/` are schema-valid but deliberately exclude a persona, and the gate catches them. A gate nobody tests is a gate that has silently stopped working. |

### The rules

| Rule | Protects | Requires |
|---|---|---|
| **A11Y-1** | P2 (Deaf) | At least one visual representation |
| **A11Y-2** | P1 (low vision) | Audio track if the block's meaning is visual |
| **A11Y-3** | P2, P4 | At least one non-speech input mode |
| **A11Y-4** | P4 (intellectual disability) | Easy-Read text on learner-facing blocks |
| **A11Y-5** | P4 | Easy-Read sentences ≤ 15 words |
| **A11Y-6** | P3 (dysarthria), P5 (stammer) | Speech is never mandatory |

Content authored in `packages/content` is held to exactly the same rules.

---

## Adding a modality

Do it in this order, or the router will receive a mode it has no handler for:

1. Add the value to `InputMode` / `OutputChannel` in `common.schema.json`
2. `npm run contracts:build`
3. Add a fallback entry in `src/guards.ts` → `FALLBACK_CHAIN`
4. Add a renderer or input adapter in `apps/web/src/modality/`
5. Add an A11Y rule in `scripts/validate.mjs` if the modality protects a persona
6. Write an ADR explaining why the modality was added

# @samvaad/content — the Workplace Language Bank

**Module M3** · 226 curated workplace phrases

The corpus the whole product is built on. It is the spaced-repetition deck, the RAG grounding
set for the role-play engine, and the vocabulary constraint that keeps the LLM in scope.

---

## Commands

```bash
npm run content:build      # compact source -> dist/blocks.json + dist/index.json
npm run content:validate   # five passes; exits non-zero on any violation
```

---

## The compact authoring format

Authors write only what a human must supply. Everything mechanical is derived by the build.

```json
{"id": "repeat_request_01", "text": "Could you please repeat that?", "intent": "request_clarification",
 "difficulty": 2, "easy_read": "I did not hear.\nI ask again.", "symbols": ["again", "say", "please"],
 "distractors": ["What did you say?", "Say again!"], "errors": ["omitting please"]}
```

The build expands that into a full `ContentBlock`: prefixed id, audio paths, caption, resolved
pictographs, accepted input modes, accessibility flags.

**Why not author `ContentBlock`s directly?** Because ~30 lines of near-identical JSON, 226 times,
guarantees copy-paste errors and guarantees nobody proof-reads the English. One entry per line
means a reviewer can read the entire corpus and actually *see* it.

| Field | Required | Notes |
|---|---|---|
| `id` | ✅ | Unique within its category; prefixed with `phrase.<slug>.` |
| `text` | ✅ | The phrase, in plain standard English |
| `intent` | ✅ | Communicative function — drives scenario matching and the error signature |
| `difficulty` | ✅ | 1–5, CEFR-mapped |
| `easy_read` | ✅ | Human-written, machine-linted. One idea per line. |
| `symbols` | — | Labels resolved through [`src/lexicon.mjs`](src/lexicon.mjs) |
| `isl` | — | ISL gloss; presence generates the clip reference |
| `distractors`, `hints`, `errors`, `tags`, `phonemes` | — | |

---

## The five validation passes

| Pass | Checks |
|---|---|
| **1 · Schema** | Every expanded block validates against `ContentBlock` |
| **2 · Accessibility** | The identical A11Y rules the contracts gate enforces — imported, not copied |
| **3 · Easy-Read** | Sentence length, abstract-word blocklist, one-idea-per-line, not-just-a-copy |
| **3b · Self-test** | Deliberately defective fixtures must each be caught |
| **4 · Quality** | Duplicate ids and phrases, unresolved symbols, difficulty spread |
| **5 · Coverage** | Progress against the 226 target, per category |

Pass 3b exists for the same reason the contracts gate and the ESLint boundary have self-tests:
**a gate nobody tests is a gate that has silently stopped working.**

The Easy-Read blocklist is not a general "hard words" list. It targets the specific abstractions
that appear when someone *shortens* a sentence without *simplifying the idea inside it* —
"Please ask for a workplace accommodation" is short, and completely useless to the learner it
was written for.

---

## The corpus

| Category | Count | |
|---|---|---|
| Greetings & introductions | 18 | |
| Asking for clarification | 20 | |
| Reporting progress | 18 | |
| Requesting help | 16 | |
| Leave & workplace adjustments | 18 | ★ |
| Disagreeing politely | 14 | |
| Giving & receiving feedback | 14 | |
| Telephone etiquette | 14 | |
| Email & written messages | 16 | |
| Meetings & standups | 16 | |
| Safety & escalation | 16 | |
| Small talk & belonging | 14 | |
| Interview language | 20 | |
| Self-advocacy & disclosure | 12 | ★ |
| **Total** | **226** | |

★ **The two categories no competitor has.** Asking for a workplace adjustment, and deciding
whether and how to disclose a disability, are the conversations that most decide whether a
disabled person gets and keeps a job — and no existing communication trainer covers them.
Lead with these in any demo.

Difficulty spread: 10 / 54 / 94 / 51 / 17 across levels 1–5.

---

## Outstanding asset work

`content:validate` reports these every run, so they cannot be quietly forgotten.

| Asset | Status | Needed by |
|---|---|---|
| **Audio** (native + slow) | 0/226 · paths generated, files not produced | Bootstrap all 226 with Piper/Coqui TTS to unblock engineering, then replace the top 100 with human recordings. `dist/index.json` carries the manifest the pipeline consumes. |
| **Phonemes** (IPA) | 0/226 | G2P pass. Required for forced alignment and GOP scoring (M6). |
| **ISL clips** | 3/226 | Recording sessions with a Deaf signer or ISL interpreter. **Start outreach now** — this needs a real person and real scheduling. |
| **Pictograph images** | 226/226 mapped, 0 verified | Every ARASAAC id in the lexicon is provisional until a human checks it against the actual picture. Automatic mapping produces embarrassing results. |

**Licensing:** ARASAAC symbols are CC BY-NC-SA (Government of Aragón / Sergio Palao). Attribution
is required wherever they are displayed.

---

## Adding a phrase

1. Add one line to the right file in [`phrases/`](phrases/)
2. `npm run content:build && npm run content:validate`
3. If a symbol label is unknown, add it to [`src/lexicon.mjs`](src/lexicon.mjs) — the table is
   reviewed by a human who knows the symbol set, which is why it is a table and not an API call

The validator will reject a phrase with no Easy-Read paraphrase, an over-long Easy-Read
sentence, an abstract word, a duplicate, or a paraphrase identical to the phrase.

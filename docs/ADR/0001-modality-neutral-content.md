# ADR-0001 · Content is modality-neutral; rendering is decided at runtime

**Status:** Accepted
**Date:** 2026-07-31

## Context

SAMVAAD must deliver the same curriculum to a low-vision learner, a Deaf learner, a non-verbal
learner using picture symbols, a learner using a two-switch scanning device, and a learner who
needs Easy-Read text.

The default industry approach is to build the app for a typical user and then add accessibility
settings. This fails predictably for two reasons:

1. **It decays.** Every new feature is one more place a developer can forget. Six months in,
   coverage is patchy and nobody knows which screens are broken for whom.
2. **It produces a reduced experience.** The "accessible version" is invariably a simplified
   subset. Our users get less curriculum, not equal curriculum.

## Decision

**A lesson is data, not a screen.**

Content is authored once as a `ContentBlock` — a canonical meaning plus a bundle of
representations (native audio, slow audio, ISL clip, pictographs, Easy-Read paraphrase,
phoneme string, caption). The author **never chooses a rendering.**

A runtime **Modality Router** selects representations from the learner's Communication Ability
Profile and composes a primary channel with any number of simultaneous support channels.

Feature code renders `<ModalityRouter block={…} />`. It may never import a renderer directly.
An ESLint boundary rule enforces this and fails the build.

## Consequences

**Easy**
- A new lesson type is accessible to all five personas the day it ships, with no per-modality work.
- Missing representations are a build-time CI warning, not a runtime surprise for a user.
- One Storybook page renders any block through all five channels — the strongest demo we have.

**Hard**
- The router is expensive up front. Three weeks, and it blocks most other client work.
- Content authoring is more demanding: every block needs every representation, or an explicit
  documented fallback.
- Developers must learn to think in content-and-profile rather than in screens. This is a real
  onboarding cost and needs to be said out loud in code review.

**Accepted cost:** a slower first month in exchange for accessibility that cannot silently rot.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Accessibility settings layered on a standard UI | Decays; produces a reduced experience for exactly the users we exist to serve |
| A separate app per disability type | Five codebases, five times the maintenance, and it segregates users by diagnosis |
| Rely on the platform screen reader alone | Covers P1 only. Does nothing for P2, P3, P4 or P5. |

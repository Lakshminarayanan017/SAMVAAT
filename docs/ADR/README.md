# Architecture Decision Records

An ADR records **why** a decision was made, so a future reader — including future you — does not
have to reverse-engineer the reasoning or repeat a discarded experiment.

Write one whenever a decision is non-obvious, expensive to reverse, or likely to be questioned.

## Index

| # | Decision | Status |
|---|---|---|
| [0001](0001-modality-neutral-content.md) | Content is modality-neutral; rendering is decided at runtime | Accepted |
| [0002](0002-canonical-text-response.md) | Every input modality normalises to a single `LearnerResponse` | Accepted |
| [0003](0003-baseline-relative-scoring.md) | Scoring is baseline-relative, never reference-speaker-relative | Accepted |
| [0004](0004-three-services-not-five.md) | Three deployable services, not five | Accepted |
| [0005](0005-web-first-free-tier-stack.md) | React PWA first, on an all-free-tier stack | Accepted |

## Template

```markdown
# ADR-NNNN · <Title>

**Status:** Proposed | Accepted | Superseded by ADR-NNNN
**Date:** YYYY-MM-DD
**Deciders:** <who>

## Context
What forced a decision? What constraints applied?

## Decision
What we are doing. Stated plainly, in the present tense.

## Consequences
What becomes easy. What becomes hard. What we accept as the cost.

## Alternatives considered
What else we looked at, and the specific reason we rejected it.
```

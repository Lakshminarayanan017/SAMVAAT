# ADR-0011 · "What to practise next", never a predicted ceiling

**Status:** Accepted
**Date:** 2026-08-01
**Blueprint:** §2.8, §16 · Appendix A item A4 · signed off 2026-08-01

## Context

The brief asks for weakness prediction and progress forecasting. The actionable half of that
already exists: a rule-based, explainable recommender where every suggestion carries a reason the
learner can read.

The other half — a predicted score, a predicted date, a predicted ceiling — is a different thing
wearing similar language.

Shown to a **learner**, a predicted ceiling is a self-fulfilling prophecy with a progress bar
attached. Disabled learners are told what they will not manage often enough without an app doing
it with a number.

Shown to an **institution**, it is a placement-allocation tool. Nobody would need to intend that;
a column predicting who will do well is a column somebody will sort by when deciding who gets the
one placement available this quarter.

## Decision

**Build "what to practise next". Never surface a predicted score, a predicted date, or a
predicted ceiling — to a learner, a trainer, or an institution.**

The recommender extends to suggest *levels* as well as phrases. It keeps its existing property:
every suggestion states its reason in words the learner can read, and no suggestion is ever framed
as a limit.

This applies to the whole product, not only the learner-facing surface. There is deliberately no
trainer-only or institution-only forecast, because "not shown to the learner" does not address the
harm — it moves it somewhere the learner cannot see or contest it.

## Consequences

**Good.** The AI's job stays what §16 says it is: make the *next thing* better, never produce a
verdict about the person. Every output is actionable by the learner within one session.

**Cost.** A projected-readiness chart is a good demo, and this gives it up.

**The related refusal already in the codebase** is `days_until_streak_at_risk()`, which exists and
deliberately returns `None`, with a comment explaining that it is the function the next person will
reach for when asked for a "your streak ends tomorrow!" notification, and that it is loss aversion
and will not be built. Forecasting gets the same treatment: if a forecast function is ever added it
returns nothing and explains why, so the refusal is discoverable at the point somebody goes looking
for the feature.

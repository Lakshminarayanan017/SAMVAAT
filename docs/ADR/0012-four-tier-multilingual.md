# ADR-0012 · Multilingual in four tiers, with the limits stated in-product

**Status:** Accepted
**Date:** 2026-08-01
**Blueprint:** §2.11, §15 · Appendix A item A5 · signed off 2026-08-01

## Context

The brief asks for twelve languages. Estimating that as one number is the single most expensive
mistake available in this project, because "supporting Tamil" means four unrelated pieces of work
whose costs differ by two orders of magnitude.

## Decision

**Architect for twelve. Ship each tier as far as it can honestly go.**

| Tier | What it is | Cost | Shipping |
|---|---|---|---|
| 1 · UI strings | ~600 strings, standard i18n | Low | **All 12** |
| 2 · AI explanation | A locale parameter in the prompt | Near zero | **All 12** |
| 3 · Phrase bank | 226 phrases *culturally adapted*, not translated — workplace idiom does not survive literal translation | **High** — a native speaker per language | **English + Tamil + Hindi** |
| 4 · Speech analysis | G2P, phoneme inventory, acoustic model per language | **Very high** — a research project each | **English only** |

Three architectural commitments, all cheap now and expensive later:

1. **Interface language and learning language are separate fields.** A learner wanting a Tamil
   interface while practising English workplace phrases is the most common real case in the target
   market. Collapsing them into one setting breaks it.

2. **RTL is a layout property, not a translation property.** Logical CSS properties
   (`margin-inline-start`, never `margin-left`) from the start. Retrofitting RTL is expensive;
   starting with logical properties is free. Already done throughout `apps/web/src/ui/`.

3. **Per-locale lazy bundles.** Nobody downloads twelve languages.

### The honesty requirement

When a learner selects a language where Tier 3 or Tier 4 is unavailable, **the product says so, in
that language, before they start.**

This is the part that is not optional. A learner told plainly that speech analysis is English-only
will accept it and carry on. A learner who discovers it by having their Tamil pronunciation scored
as bad English will leave, and will be right to.

## Consequences

**Good.** The twelve-language claim is real for the tiers where it is real, and the product never
silently mis-scores somebody for speaking their own language.

**Cost.** Tier 3 needs a native speaker per language and cannot be bought cheaply or generated.
Tier 4 will not extend past English without a research programme; that is stated rather than
worked around.

**Risk.** The blueprint rates multilingual under-estimation as high-likelihood, high-impact (R6).
The mitigation is this table: four tiers costed separately, never quoted as one number.

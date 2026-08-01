# ADR-0010 · Three motion levels, Gentle by default

**Status:** Accepted
**Date:** 2026-08-01
**Blueprint:** §2.4, §10 · Appendix A item A3 · signed off 2026-08-01

## Context

The brief asks for particle effects and confetti. A large number of independently moving objects
is the single worst pattern for vestibular sensitivity — and vestibular disorders are common,
under-declared, and not something a learner is likely to have told us about before the first
celebration fires.

A celebration that makes somebody nauseous does not merely annoy them. It closes the app, and
they do not come back.

Against that: the celebration is the payoff moment, and the blueprint is right that ending a
unit of work has to feel better than starting one. Removing it entirely gives up the mechanic
that makes the loop work at all.

## Decision

**Three levels the learner controls, defaulting to the middle one.**

| Level | Behaviour |
|---|---|
| **Full** | Everything. Bounded particle burst on major wins — ≤24 particles, single emission, no loop, no full-screen coverage |
| **Gentle** *(default)* | Transforms and fades. Stars land, XP counts. No particles, no parallax |
| **Still** | Opacity only |

`prefers-reduced-motion: reduce` forces **Still** — *unless* the learner has explicitly chosen
otherwise in the app. The OS setting is a default, not a verdict: somebody who enabled reduced
motion months ago for a different app must be able to turn animation back on here, and somebody
who never found the OS setting must still be safe by default.

**Reduced motion keeps cross-fades rather than returning `none`.** A hard cut loses the signal
that something changed, and for a learner with a cognitive disability that signal is doing real
work. The change simply must not travel through space to deliver it.

**420ms is the ceiling anywhere in the product.** Not an aesthetic preference: a switch-scanning
learner waits out every animation before the next scan step is safe to read, so a 900ms
celebration costs them real time on every single item, forever.

## Consequences

**Good.** The brief gets its confetti. The learners most likely to be harmed by it do not get it
by default. Everybody can move in either direction, in two actions, from anywhere.

**Cost.** Every animated component must either be authored three times or authored once against
a motion token that collapses correctly. The second is what `design-system/motion.ts` exists
for, and the existing "the app is fully usable with all animation disabled" test is what stops
the three levels drifting apart.

**The rule that makes all of this safe** is unchanged: animation may only ever *emphasise*
something already true in the DOM. Remove every animation and the app must still be completely
usable and say exactly the same things.

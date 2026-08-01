# SAMVAAD UI Analysis & Specification

**Purpose.** Extract the product-design principles behind Duolingo's interface, section by
section, then translate each one into a specification for SAMVAAD v2.

**What this is not.** Not a copy exercise. No Duolingo assets, artwork, logos, colours,
illustrations or brand elements are reproduced anywhere. What is extracted is *why* the interface
works — the layout logic, the interaction timing, the motivation architecture, the visual
hierarchy — and that reasoning is then applied to an original SAMVAAD identity.

---

## How to read these files

Each file has the same four sections:

| Section | Contains |
|---|---|
| **1. What Duolingo does** | Observed behaviour, measurements, states, timings |
| **2. Why it works** | The product-design reason. This is the part worth keeping |
| **3. Where it fails our learners** | Honest. Several patterns are actively harmful for disabled users |
| **4. SAMVAAD specification** | Implementation-ready spec: sizes, tokens, states, copy rules |

Section 4 is what gets built. Sections 1–3 exist so nobody later removes a decision without
understanding the reason it was made.

---

## Files

### Foundations
| # | File | Covers |
|---|---|---|
| 01 | [design-philosophy](01-design-philosophy.md) | The five load-bearing principles |
| 02 | [colour-system](02-colour-system.md) | Palette, semantic roles, unit colours, contrast |
| 03 | [typography](03-typography.md) | Scale, weights, line height, Easy-Read mapping |
| 04 | [spacing-layout-grid](04-spacing-layout-grid.md) | Rhythm, gutters, breakpoints, zoom |
| 05 | [shape-elevation-depth](05-shape-elevation-depth.md) | Radius, shadow, the tactile button |
| 06 | [motion-and-timing](06-motion-and-timing.md) | Durations, curves, choreography |
| 07 | [iconography-and-illustration](07-iconography-and-illustration.md) | Icon grid, character system |
| 08 | [sound-and-haptics](08-sound-and-haptics.md) | Audio feedback, why it is off by default |

### Structure
| # | File | Covers |
|---|---|---|
| 09 | [navigation-and-ia](09-navigation-and-ia.md) | Bottom nav, chrome, full-screen surfaces |
| 10 | [home-and-the-path](10-home-and-the-path.md) | The single most important screen |
| 11 | [units-chapters-sections](11-units-chapters-sections.md) | Grouping, headers, colour banding |
| 12 | [level-nodes-and-cards](12-level-nodes-and-cards.md) | Every node state |

### The lesson
| # | File | Covers |
|---|---|---|
| 13 | [lesson-flow](13-lesson-flow.md) | Open → question → answer → feedback → next → end |
| 14 | [exercise-types](14-exercise-types.md) | Every question format and its interaction |
| 15 | [feedback-system](15-feedback-system.md) | The correct/incorrect banner |
| 16 | [celebration-and-completion](16-celebration-and-completion.md) | The end-of-lesson sequence |
| 17 | [dialogue-and-ai-conversation](17-dialogue-and-ai-conversation.md) | Multi-turn practice |

### Motivation
| # | File | Covers |
|---|---|---|
| 18 | [xp-and-levels](18-xp-and-levels.md) | The effort currency |
| 19 | [streaks](19-streaks.md) | And why ours cannot punish |
| 20 | [hearts-and-failure-walls](20-hearts-and-failure-walls.md) | **The pattern we refuse, and what replaces it** |
| 21 | [currency-and-shop](21-currency-and-shop.md) | Cosmetics only |
| 22 | [quests-and-daily-goals](22-quests-and-daily-goals.md) | Additive-only goals |
| 23 | [leagues-and-social](23-leagues-and-social.md) | **The pattern we refuse, and what replaces it** |
| 24 | [achievements-and-badges](24-achievements-and-badges.md) | Four families |
| 25 | [progression-psychology](25-progression-psychology.md) | Why any of this works at all |

### Screens
| # | File | Covers |
|---|---|---|
| 26 | [onboarding](26-onboarding.md) | First 90 seconds |
| 27 | [profile-and-progress](27-profile-and-progress.md) | The learner's own record |
| 28 | [settings-and-accessibility](28-settings-and-accessibility.md) | Where our product must be best in class |
| 29 | [trainer-and-institution](29-trainer-and-institution.md) | Surfaces Duolingo has no equivalent of |

### Components & states
| # | File | Covers |
|---|---|---|
| 30 | [component-library](30-component-library.md) | Every primitive, with its API |
| 31 | [system-states](31-system-states.md) | Loading, empty, error, offline, success |
| 32 | [modals-sheets-toasts](32-modals-sheets-toasts.md) | Overlays and transient messages |

### Synthesis
| # | File | Covers |
|---|---|---|
| 33 | [accessibility-critique](33-accessibility-critique.md) | Everything Duolingo does that excludes our learners |
| 34 | [samvaad-identity](34-samvaad-identity.md) | Our own brand: colour, mascot, voice |
| 35 | [build-order](35-build-order.md) | What gets built in what order, and what gets deleted |

---

## The one-paragraph summary

Duolingo's engagement does not come from its graphics. It comes from four mechanics: **the
session is short and its end is always visible**; **something is always in motion** so progress
is never invisible; **the next action is chosen for you** so there is no decision before
starting; and **finishing is rewarded rather than starting**. All four are architectural, none
requires a mascot, and all four are absent from SAMVAAD today.

Three of Duolingo's other mechanics — hearts, leagues and streak loss-aversion — work by
*threat*. They are effective on a general population and actively harmful on ours. We take the
four that work by *momentum* and refuse the three that work by fear.

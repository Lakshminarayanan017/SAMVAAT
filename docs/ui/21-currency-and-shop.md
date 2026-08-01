# 21 · Currency, shop and cosmetics

---

## 1. What Duolingo does

### Gems

Earned slowly (finishing lessons, chests, quests) and buyable. Spent on:

- Heart refills
- Streak freezes
- Timed-boost power-ups
- Outfits for the mascot
- Legendary-level attempts

### The shop

A tab with three sections: power-ups, hearts, cosmetics. Prices in gems, with a "get more gems"
route to real money.

### Chests and rewards

Daily chest, lesson-completion chests, friend-quest chests. Variable reward — the amount is
random, which is a deliberate slot-machine pattern.

---

## 2. Why it works

- **A second currency separates effort from spending.** XP is a record; gems are usable, so the
  learner has something to *decide* about.
- **Variable rewards** produce stronger habit formation than fixed ones. This is well-established
  and it is also exactly the mechanism behind slot machines.
- **Cosmetics are cheap to produce and infinitely re-sellable.**

---

## 3. Where it fails our learners

| Problem | Consequence |
|---|---|
| **Gems buy hearts** | Currency gates learning content. A learner who cannot afford gems gets less practice |
| **Gems buy streak repair** | Paying to undo a punishment for being ill |
| Variable-ratio chests | Deliberate compulsion mechanics, aimed at a population that includes people with cognitive disabilities and impulse-control differences |
| A shop as a primary tab | Commerce given the same navigational weight as learning |
| Real-money conversion | A product used in special schools and skilling centres should not have a purchase funnel aimed at the learner |

---

## 4. SAMVAAD specification

### One hard rule

> **No coin, gem, token or unlock may ever gate learning content.**

The moment a learner cannot reach a lesson without a currency, the product has invented a failure
wall — which file 20 refuses on ethical grounds and Ethics E7 forbids outright.

### Coins exist and buy only cosmetics

| Earned by | Coins |
|---|---|
| Finishing a level | 5 |
| Completing a daily quest | 10 |
| A weekly quest | 25 |
| A milestone badge | 25 |

**Fixed amounts, never variable.** No chests, no random drops, no "you got lucky". Variable-ratio
reinforcement is a compulsion mechanic and we are not deploying it against this population.

### What coins buy

- Mitra outfits
- World themes
- Avatar parts

And nothing else. No hearts (there are none), no streak repair (nothing to repair), no boosts (no
timers to boost), no content.

### The shop is not a tab

It lives inside `/me`, one level down, under **Rewards**. Commerce does not get the same
navigational weight as learning.

### No real money, at all

There is no purchase route. Coins are earned by practising and by nothing else.

This costs a revenue line and is the right call: the product is used in special schools and
skilling centres, and a purchase funnel aimed at a disabled learner in that setting is
indefensible. If the product ever monetises, it monetises to **institutions**, for the cohort
reporting they actually want — never to learners, for their own learning.

### The avatar

Learner avatar plus Mitra outfits. **Deliberately shallow** — a deep cosmetic economy competes
with learning for attention, and a learner grinding for coins is a learner not practising.

**The representation rule, which is the whole point of having an avatar at all:**

Wheelchairs, hearing aids, cochlear implants, white canes, AAC devices, prosthetics and guide
dogs are included as **ordinary options presented alongside hats and shirts**.

- Not in a "disability" category
- Not in an "accessibility" section
- Not unlockable — available from the start
- Not more expensive

They sit in the same lists as everything else, sorted the same way. That framing *is* the
feature. A learner who finds their wheelchair filed under a special section has been told
something about how the product sees them.

### Presentation

```
🪙 120
```

`aria-label="120 coins"`. Never a bare number. Shown on `/me`, never in the lesson chrome — a
currency counter during a mission is a distraction with nothing to spend it on.

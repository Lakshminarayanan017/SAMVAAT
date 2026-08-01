# 19 · Streaks

Duolingo's most powerful mechanic, and the one built most directly on anxiety.

---

## 1. What Duolingo does

### A count of consecutive days

A flame icon and a number in the header. Practise today, it goes up. Miss a day, **it resets to
zero.**

### The pressure apparatus

- Push notification in the evening: *"Your 47 day streak is at risk!"*
- A "streak at risk" banner in-app
- A weekly calendar showing days hit and missed
- Milestone celebrations at 7, 30, 100, 365
- **Streak freeze** — a purchasable item that absorbs one missed day
- **Streak repair** — pay to restore a broken streak

### It is the most-referenced number in the product

Header, profile, notifications, leagues, friends' profiles.

---

## 2. Why it works

It works extremely well, and the mechanism is worth naming precisely: **loss aversion**. A 200-day
streak is a possession. Losing it costs more, psychologically, than gaining a day is worth. The
learner is not returning because tomorrow is appealing; they are returning because losing the
number hurts.

The streak freeze exists to monetise that pain. So does streak repair.

---

## 3. Where it fails our learners

This is the clearest example in the whole analysis of a mechanic that is effective for a general
population and **harmful for ours**.

| Problem | Consequence |
|---|---|
| **Reset to zero on a missed day** | Our learners miss days for reasons entirely outside their control: fatigue conditions, hospital admissions, seizure recovery, depression, carer availability, a bad pain week. Punishing that is punishing the disability |
| **"Your streak is at risk" notifications** | Manufactured anxiety, delivered to a population with elevated baseline anxiety |
| **Paying to repair** | Charging a disabled person to undo a punishment for being ill |
| **A visible falling number** | The one thing they built is shown being taken away |
| **Streak as a public signal** | On profiles and in leagues, it becomes a proxy for worth |

A learner returning after two weeks in hospital should be met with *"welcome back"*, not with the
number 0 where 47 used to be.

---

## 4. SAMVAAD specification

### We keep the *returning* mechanic and delete the *punishment*

### Three numbers, and only one is prominent

| Number | Behaviour |
|---|---|
| **Days practised** | Total, lifetime. **Only ever goes up.** This is the headline |
| **Current run** | Consecutive days. Tracked and celebrated when it grows |
| **Longest run** | A permanent record. **Survives any break, forever** |

The headline is *days practised*, not *current run*. It is a number that can never fall, so it can
never be lost, so it cannot be used against the learner.

### The current run never announces its loss

Specified precisely, because this is where it would be easiest to slip:

- It is **never shown falling**
- It is **never described as at risk**
- There is **no notification** about it, ever
- On return after a break, the display simply shows the new run — with no reference to what the
  old one was
- `summary()` never mentions a broken run

### Grace, automatically

`GRACE_DAYS = 2`. A gap of up to two days does not break the run. Not purchasable, not a
consumable, not something to remember to activate — it simply exists, for everybody.

Longer gaps earn additional grace through **use**, not payment. A learner who has practised on
sixty days has more slack than one who has practised on three, because they have demonstrated the
habit and deserve the benefit of the doubt.

### Returning after a break is a welcome

```
Welcome back.

Everything you learned is still here.
You have practised on 46 days.

[ Continue where you were ]
```

No mention of the gap. No "it's been 14 days". No apology required. `returned_after_break` is a
real flag in the progress model, and it produces warmth rather than a report.

### The function that will be asked for, and refused

`days_until_streak_at_risk()` **exists in the codebase and deliberately returns `None`**, with a
comment explaining that it is the function the next person will reach for when somebody asks for
a "your streak ends tomorrow!" notification, that it is loss aversion, and that it will not be
built.

The refusal is discoverable at the exact point somebody goes looking for the feature. That is
worth more than a rule in a document nobody reads.

### Presentation

```
🔥 46 days practised
   6 in a row · longest 21
```

`aria-label="46 days practised, 6 days in a row, longest run 21 days"`.

The flame is decorative and `aria-hidden`. Milestones (7, 30, 100 days practised) get a small
badge — awarded for **reaching**, never mentioned as approaching, because "3 days to your badge!"
is the same mechanic wearing a friendlier coat.

### Notifications

If notifications ship at all, Mitra says something **specific and forward-looking**:

> *"World 3 has a phone call waiting."*

Never *"You haven't practised in 3 days"*. Never a streak warning. Never guilt.

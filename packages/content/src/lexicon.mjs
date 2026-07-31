/**
 * Symbol lexicon — maps a plain label to an AAC pictograph.
 *
 * Authors write `"symbols": ["again", "say"]` and the build resolves them here.
 * Two reasons it is a lookup table rather than an API call at build time:
 *
 *   1. Automatic label→symbol mapping produces embarrassing and occasionally
 *      offensive results. Every entry here is meant to be eyeballed by a human
 *      who knows the symbol set. Reviewing one table is tractable; reviewing
 *      226 scattered inline ids is not.
 *   2. The build must work offline and be deterministic.
 *
 * IDs are ARASAAC identifiers. They are PROVISIONAL until the asset pipeline
 * runs and a human verifies each mapping against the actual picture — tracked
 * by the `verified` flag and reported by `npm run content:validate`.
 *
 * ARASAAC symbols are CC BY-NC-SA (Government of Aragón / Sergio Palao).
 * Attribution is required wherever they are displayed.
 */

/** label -> { id, verified } */
export const LEXICON = new Map(
  Object.entries({
    // ── people & pronouns ──────────────────────────────────────────────
    i: 6625, you: 8146, we: 8014, they: 7745,
    manager: 5921, supervisor: 27459, colleague: 25146, customer: 25147,
    team: 7574, hr: 27460,

    // ── core verbs ─────────────────────────────────────────────────────
    say: 11331, ask: 6428, tell: 7621, want: 8043, need: 6009,
    help: 5441, work: 8071, start: 7386, finish: 5219, wait: 8033,
    go: 5352, come: 4958, give: 5344, take: 7565, make: 5892,
    understand: 7887, know: 5710, think: 7660, learn: 5751, show: 7233,
    hear: 5432, listen: 5788, look: 5850, read: 7009, write: 8121,
    repeat: 2462, explain: 5148, check: 4884, fix: 5225, report: 7052,

    // ── courtesy ───────────────────────────────────────────────────────
    please: 7095, 'thank you': 6510, sorry: 7317, hello: 5443,
    goodbye: 5379, welcome: 8054, 'excuse me': 5147,

    // ── responses ──────────────────────────────────────────────────────
    yes: 5584, no: 5526, maybe: 5898, ok: 6612, again: 11317,
    not: 6577, more: 5972, slow: 7290, slowly: 7290,
    who: 8087, can: 4830, cannot: 4831,

    // ── workplace nouns ────────────────────────────────────────────────
    job: 5665, task: 7570, machine: 5875, tool: 7712, box: 4762,
    order: 6631, report: 7052, meeting: 5921, break: 4771, lunch: 5860,
    shift: 7218, leave: 5757, holiday: 5470, salary: 7141, form: 5261,
    email: 5107, phone: 6905, computer: 4991, safety: 7135, accident: 4671,
    problem: 6959, mistake: 5947, question: 6987, answer: 4703,
    instruction: 5578, training: 7758, uniform: 7891, badge: 4718,
    door: 5071, floor: 5236, warehouse: 8038, office: 6608,

    // ── time ───────────────────────────────────────────────────────────
    today: 7698, tomorrow: 7705, yesterday: 8145, now: 6592,
    morning: 5975, afternoon: 4680, evening: 5133, week: 8050,
    monday: 5963, friday: 5271, late: 5744, early: 5094, time: 7683,

    // ── feelings & judgement ───────────────────────────────────────────
    good: 6479, bad: 4716, happy: 5424, sad: 7133, tired: 7691,
    worried: 8118, confused: 4998, ready: 7010, sure: 7500, difficult: 5045,
    easy: 5096, important: 5544, careful: 4848,

    // ── accessibility & self-advocacy ──────────────────────────────────
    deaf: 5023, blind: 4745, disability: 25148, wheelchair: 8060,
    'sign language': 7245, captions: 25149, 'hearing aid': 5433,
    written: 8121, quiet: 6989, light: 5801, rest: 7069,
    accommodation: 25150, support: 7498,
  }).map(([label, id]) => [label, { id, verified: false }]),
);

/**
 * Resolve a label to a pictograph, or return null.
 *
 * A missing label is never a build failure — the block simply carries fewer
 * symbols and the coverage report flags it. Blocking the whole corpus because
 * one word lacks a picture would be the wrong trade.
 */
export function resolveSymbol(label) {
  const entry = LEXICON.get(label.toLowerCase());
  if (!entry) return null;

  return {
    set: 'arasaac',
    id: entry.id,
    label,
    // The asset pipeline fills real URIs; until then the renderer draws a
    // labelled placeholder rather than a broken image.
    uri: `content/symbols/arasaac/${entry.id}.png`,
  };
}

export function unknownLabels(labels) {
  return labels.filter((label) => !LEXICON.has(label.toLowerCase()));
}

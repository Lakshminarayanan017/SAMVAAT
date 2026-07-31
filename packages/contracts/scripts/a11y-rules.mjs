/**
 * The accessibility rules every ContentBlock must satisfy.
 *
 * Extracted so the contracts validator AND the content build enforce exactly
 * the same rules. Two copies of these would drift, and the drift would show up
 * as content that passes one gate and excludes a learner anyway.
 *
 * Each rule names the persona it protects. A rule protecting nobody in
 * docs/PERSONAS.md does not belong here.
 */

export const A11Y_RULES = [
  {
    id: 'A11Y-1',
    persona: 'P2 (Deaf)',
    why: 'must be reachable without hearing anything',
    message: 'needs at least one visual representation (caption, easy_read, isl_clip or pictographs)',
    check: (b) => {
      const r = b.representations ?? {};
      return Boolean(r.caption || r.easy_read || r.isl_clip || r.pictographs?.length);
    },
  },
  {
    id: 'A11Y-2',
    persona: 'P1 (low vision)',
    why: 'must be reachable without seeing the screen',
    message: 'is flagged requires_vision but has no audio_native representation',
    // canonical_text is always screen-reader reachable, but a block whose meaning
    // is genuinely visual needs a real audio track to stand in for it.
    check: (b) => b.a11y?.requires_vision !== true || Boolean(b.representations?.audio_native),
  },
  {
    id: 'A11Y-3',
    persona: 'P2 (Deaf), P4 (AAC user)',
    why: 'must be answerable without speaking',
    message: 'accepts only speech input, which excludes every non-speaking learner',
    check: (b) => (b.interaction?.accepted_input_modes ?? []).some((m) => m !== 'speech'),
  },
  {
    id: 'A11Y-4',
    persona: 'P4 (intellectual disability)',
    why: 'must be readable at an Easy-Read level',
    message: 'is learner-facing but has no easy_read representation',
    check: (b) =>
      !['phrase', 'instruction', 'interview_question'].includes(b.kind) ||
      Boolean(b.representations?.easy_read),
  },
  {
    id: 'A11Y-5',
    persona: 'P4 (intellectual disability)',
    why: 'Easy-Read means at most 15 words per sentence',
    message: 'has an easy_read sentence longer than 15 words',
    check: (b) => {
      const t = b.representations?.easy_read;
      if (!t) return true;
      return easyReadSentences(t).every((s) => wordCount(s) <= 15);
    },
  },
  {
    id: 'A11Y-6',
    persona: 'P3 (dysarthria), P5 (stammer)',
    why: 'speech must never be the only route to success',
    message: 'sets requires_speech=true; no block may make speech mandatory',
    check: (b) => b.a11y?.requires_speech !== true,
  },
];

/** @returns {string[]} ids of the rules this block violates */
export function a11yViolations(block) {
  return A11Y_RULES.filter((rule) => !rule.check(block)).map((rule) => rule.id);
}

/** @returns the rule objects this block violates, for detailed reporting */
export function brokenRules(block) {
  return A11Y_RULES.filter((rule) => !rule.check(block));
}

// ── Easy-Read helpers, shared with the content linter ────────────────────────

/** Easy-Read is authored one idea per line, so a line break IS a sentence break. */
export function easyReadSentences(text) {
  return text
    .split(/\n|(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function wordCount(sentence) {
  return sentence.split(/\s+/).filter(Boolean).length;
}

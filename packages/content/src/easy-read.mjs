/**
 * The Easy-Read linter.
 *
 * Easy-Read is a real standard with measurable rules. "Someone wrote a shorter
 * sentence" is not compliance, and at 226 entries nobody is going to re-read the
 * whole corpus by eye every time it changes. Linting is the only way it stays
 * honest as it grows.
 *
 * Kept as a pure function so the validator and its self-test both use it.
 */
import { easyReadSentences, wordCount } from '../../contracts/scripts/a11y-rules.mjs';

/** Hard cap. Also enforced as rule A11Y-5 in the contracts gate. */
export const MAX_WORDS = 15;

/** Warn above this, so the corpus stays comfortably inside the cap. */
export const COMFORTABLE_WORDS = 12;

/**
 * Words that defeat the purpose of an Easy-Read paraphrase.
 *
 * Not a general "hard words" list — these are specifically the abstractions and
 * idioms that appear when someone shortens a sentence without simplifying the
 * idea inside it. "Please ask for a workplace accommodation" is short, and
 * completely useless to the learner it was written for.
 */
export const ABSTRACT_WORDS = [
  'clarification', 'accommodation', 'etiquette', 'appropriate', 'sufficient',
  'regarding', 'concerning', 'furthermore', 'consequently', 'nevertheless',
  'utilise', 'utilize', 'implement', 'facilitate', 'endeavour', 'endeavor',
  'circumstances', 'nonetheless', 'subsequently', 'prioritise', 'prioritize',
  'aforementioned', 'notwithstanding', 'liaise', 'commence', 'terminate',
];

/**
 * @returns {{level: 'error'|'warning', message: string}[]}
 */
export function lintEasyRead(block) {
  const problems = [];
  const text = block.representations?.easy_read;

  if (!text) {
    // A11Y-4 already covers a missing paraphrase on learner-facing kinds;
    // nothing further to lint.
    return problems;
  }

  const sentences = easyReadSentences(text);

  for (const sentence of sentences) {
    const words = wordCount(sentence);
    if (words > MAX_WORDS) {
      problems.push({ level: 'error', message: `sentence of ${words} words: "${sentence}"` });
    } else if (words > COMFORTABLE_WORDS) {
      problems.push({ level: 'warning', message: `sentence of ${words} words is close to the limit` });
    }
  }

  const lower = text.toLowerCase();
  for (const word of ABSTRACT_WORDS) {
    if (lower.includes(word)) {
      problems.push({ level: 'error', message: `contains the abstract word "${word}"` });
    }
  }

  // One idea per line is the point of the format. A paraphrase that is a single
  // long line has been shortened, not simplified.
  if (sentences.length === 1 && wordCount(sentences[0]) > 8) {
    problems.push({
      level: 'warning',
      message: 'is a single long line; split it one idea per line',
    });
  }

  // A paraphrase identical to the phrase has done no work at all.
  if (text.trim().toLowerCase() === (block.canonical_text ?? '').trim().toLowerCase()) {
    problems.push({
      level: 'error',
      message: 'is identical to the phrase; it has not been simplified',
    });
  }

  return problems;
}

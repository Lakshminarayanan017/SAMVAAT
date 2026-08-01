/**
 * Comparing a learner's answer to the target.
 *
 * The client decides `correct`; the server decides the FSRS grade from it. That
 * split is deliberate — matching is a presentation concern (what counts as
 * "the same phrase" depends on the modality), while scheduling is a scoring
 * concern and belongs where the ethics rules are enforced.
 *
 * THE NORMALISATION IS DELIBERATELY GENEROUS
 * ------------------------------------------
 * Answers arrive from ASR on atypical speech, from AAC symbol composition, and
 * from typing with a switch device. Every one of those introduces noise that
 * has nothing to do with whether the learner knew the phrase.
 *
 * So: case, punctuation and spacing are ignored, and so are the articles and
 * fillers that AAC composition routinely drops. What is NOT ignored is word
 * choice and word order, because those are the thing being learned.
 */

/**
 * Words an AAC board or a terse typist will often omit, and whose absence says
 * nothing about whether the learner has the phrase.
 *
 * Kept short on purpose. Every word added here is a word the learner can leave
 * out and still be marked right, and a list that grows unchecked ends up
 * accepting answers that are not the phrase at all.
 */
const OPTIONAL_WORDS = new Set(['a', 'an', 'the', 'um', 'uh', 'er', 'erm']);

/** Contractions ASR and typists disagree about. Expanded on both sides. */
const EXPANSIONS: Record<string, string> = {
  "i'm": 'i am',
  "i've": 'i have',
  "i'll": 'i will',
  "don't": 'do not',
  "can't": 'cannot',
  "won't": 'will not',
  "isn't": 'is not',
  "it's": 'it is',
  "that's": 'that is',
  "could'you": 'could you',
  "you're": 'you are',
  "we're": 'we are',
  "didn't": 'did not',
  "doesn't": 'does not',
  "haven't": 'have not',
  "i'd": 'i would',
};

export function normaliseAnswer(text: string): string {
  const expanded = text
    .toLowerCase()
    .normalize('NFKC')
    // Fold the curly apostrophe first, or the expansions below miss.
    .replace(/[‘’‛]/g, "'")
    .split(/\s+/)
    .map((word) => EXPANSIONS[word.replace(/[^a-z']/g, '')] ?? word)
    .join(' ');

  return expanded
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter((word) => word && !OPTIONAL_WORDS.has(word))
    .join(' ');
}

/** Whether an answer counts as the target phrase. */
export function matches(answer: string, target: string): boolean {
  return normaliseAnswer(answer) === normaliseAnswer(target);
}

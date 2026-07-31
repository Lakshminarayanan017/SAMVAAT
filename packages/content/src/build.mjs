#!/usr/bin/env node
/**
 * Expands the compact authoring format into full ContentBlocks.
 *
 * Authors write the minimum that only a human can supply — the phrase, its
 * intent, its Easy-Read paraphrase, its symbols. Everything mechanical (ids,
 * asset paths, captions, input modes, accessibility flags) is derived here.
 *
 * Why not author ContentBlocks directly? Because ~30 lines of near-identical
 * JSON per phrase, 226 times, guarantees copy-paste errors and guarantees
 * nobody proof-reads the English. The compact form fits on one line, so a
 * reviewer can read the entire corpus and actually see it.
 */
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { resolveSymbol } from './lexicon.mjs';

const here = dirname(fileURLToPath(import.meta.url));
export const PHRASE_DIR = join(here, '..', 'phrases');
export const DIST_DIR = join(here, '..', 'dist');

/**
 * Every phrase accepts every input mode.
 *
 * This is the default rather than a per-phrase decision because the moment a
 * phrase narrows its modes, a persona loses access to it — and rule A11Y-3
 * exists precisely because that decision should never be made casually. A
 * phrase that genuinely cannot be answered by symbols must say so explicitly.
 */
const ALL_INPUT_MODES = ['speech', 'text', 'aac', 'sign', 'switch'];

export function loadCategories() {
  return readdirSync(PHRASE_DIR)
    .filter((file) => file.endsWith('.json'))
    .sort()
    .map((file) => ({ file, ...JSON.parse(readFileSync(join(PHRASE_DIR, file), 'utf8')) }));
}

/** Compact entry + its category -> a full ContentBlock. */
export function expand(entry, category) {
  const id = `phrase.${category.slug}.${entry.id}`;
  const symbols = (entry.symbols ?? [])
    .map(resolveSymbol)
    .filter((symbol) => symbol !== null);

  const representations = {
    // Asset paths are derived, never authored: a typo in a hand-written path
    // produces a silently missing audio track, which a learner experiences as
    // the app being broken.
    audio_native: { uri: `content/audio/${id}.native.mp3`, mime_type: 'audio/mpeg' },
    audio_slow: { uri: `content/audio/${id}.slow.mp3`, mime_type: 'audio/mpeg' },
    // Captions are verbatim, never a paraphrase — captions that paraphrase are
    // a documented failure for Deaf users.
    caption: entry.text,
    easy_read: entry.easy_read,
    ...(symbols.length ? { pictographs: symbols } : {}),
    ...(entry.isl
      ? { isl_clip: { uri: `content/isl/${id}.mp4`, gloss: entry.isl } }
      : {}),
    ...(entry.phonemes ? { phonemes: entry.phonemes } : {}),
  };

  return {
    id,
    kind: 'phrase',
    canonical_text: entry.text,
    intent: entry.intent,
    difficulty: entry.difficulty,
    scenario_tags: [category.slug, ...(entry.tags ?? [])],
    representations,
    interaction: {
      accepted_input_modes: entry.modes ?? ALL_INPUT_MODES,
      target_response: { type: 'phrase_match', ref: id },
      ...(entry.hints ? { hints: entry.hints } : {}),
      ...(entry.distractors ? { distractors: entry.distractors } : {}),
      ...(entry.errors ? { common_errors: entry.errors } : {}),
    },
    a11y: {
      requires_audio: false,
      requires_vision: false,
      // Never true. A phrase that could only be answered by speaking would
      // exclude P2, P3 and P4 — see Ethics E7 and rule A11Y-6.
      requires_speech: false,
    },
    version: 1,
    source: 'authored',
  };
}

export function buildAll() {
  const blocks = [];
  const categories = [];

  for (const category of loadCategories()) {
    const expanded = category.entries.map((entry) => expand(entry, category));
    blocks.push(...expanded);
    categories.push({
      slug: category.slug,
      title: category.title,
      target: category.target,
      actual: expanded.length,
    });
  }

  return { blocks, categories };
}

function main() {
  const { blocks, categories } = buildAll();

  mkdirSync(DIST_DIR, { recursive: true });
  writeFileSync(join(DIST_DIR, 'blocks.json'), JSON.stringify(blocks, null, 2), 'utf8');
  writeFileSync(
    join(DIST_DIR, 'index.json'),
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        total: blocks.length,
        categories,
        // The asset manifest the TTS/recording pipeline consumes. Emitting it
        // from the same source guarantees the audio produced matches the audio
        // the blocks reference.
        audio_required: blocks.map((b) => ({
          id: b.id,
          text: b.canonical_text,
          native: b.representations.audio_native.uri,
          slow: b.representations.audio_slow.uri,
        })),
      },
      null,
      2,
    ),
    'utf8',
  );

  console.log(`built ${blocks.length} blocks across ${categories.length} categories`);
  console.log(`  ${join(DIST_DIR, 'blocks.json')}`);
}

// Comparing import.meta.url against argv[1] is unreliable across Windows shells
// (drive-letter casing, slash direction), so match on the entry filename instead.
if (process.argv[1]?.endsWith('build.mjs')) main();

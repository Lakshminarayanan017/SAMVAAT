#!/usr/bin/env node
/**
 * Validates the Workplace Language Bank.
 *
 * Five passes:
 *   1. SCHEMA      every expanded block validates against ContentBlock
 *   2. ACCESSIBILITY  the same A11Y rules the contracts gate enforces
 *   3. EASY-READ   the plain-language rules a schema cannot express
 *   4. QUALITY     duplicates, unresolved symbols, difficulty distribution
 *   5. COVERAGE    progress against the 226-entry target, per category
 *
 * Pass 3 is the one that needs explaining. Easy-Read is a real standard with
 * measurable rules, and "someone wrote a simpler sentence" is not compliance.
 * Linting it is the only way a corpus this size stays honest as it grows.
 */
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildValidator, formatErrors } from '../../contracts/scripts/schema-registry.mjs';
import { brokenRules } from '../../contracts/scripts/a11y-rules.mjs';
import { lintEasyRead } from './easy-read.mjs';
import { unknownLabels } from './lexicon.mjs';
import { buildAll, loadCategories } from './build.mjs';

const FIXTURE_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures');

const TARGET_TOTAL = 226;

const red = (s) => `\x1b[31m${s}\x1b[0m`;
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;

let failures = 0;
const warnings = [];

function fail(what, detail) {
  failures++;
  console.log(`  ${red('FAIL')} ${what}`);
  if (detail) console.log(`       ${detail}`);
}
function warn(what) {
  warnings.push(what);
}

const { blocks, categories } = buildAll();
const rawCategories = loadCategories();

// ── PASS 1 · SCHEMA ───────────────────────────────────────────────────────────

console.log('\nSCHEMA');

const ajv = buildValidator();
const validate = ajv.getSchema('content-block.schema.json');
let schemaBad = 0;

for (const block of blocks) {
  if (!validate(block)) {
    schemaBad++;
    fail(block.id, formatErrors(validate.errors).trim());
  }
}
if (!schemaBad) console.log(`  ${green('ok')}   ${dim(`${blocks.length} blocks validate`)}`);

// ── PASS 2 · ACCESSIBILITY ────────────────────────────────────────────────────

console.log('\nACCESSIBILITY');

let a11yBad = 0;
for (const block of blocks) {
  for (const rule of brokenRules(block)) {
    a11yBad++;
    fail(`${block.id} → ${rule.id}`, `${rule.message}  ${dim(`(protects ${rule.persona})`)}`);
  }
}
if (!a11yBad) {
  console.log(`  ${green('ok')}   ${dim(`${blocks.length} blocks reachable by all five personas`)}`);
}

// ── PASS 3 · EASY-READ ────────────────────────────────────────────────────────

console.log('\nEASY-READ');

let easyReadBad = 0;

for (const block of blocks) {
  for (const problem of lintEasyRead(block)) {
    if (problem.level === 'error') {
      easyReadBad++;
      fail(`${block.id} easy_read`, problem.message);
    } else {
      warn(`${block.id}: easy_read ${problem.message}`);
    }
  }
}

if (!easyReadBad) {
  console.log(`  ${green('ok')}   ${dim(`${blocks.length} Easy-Read paraphrases conform`)}`);
}

// ── PASS 3b · LINTER SELF-TEST ────────────────────────────────────────────────
// Deliberately defective entries that must each be caught. A linter nobody
// tests is a linter that has silently stopped working.

const { cases } = JSON.parse(readFileSync(join(FIXTURE_DIR, 'bad-entries.json'), 'utf8'));
let selfTestBad = 0;

for (const testCase of cases) {
  const caught = lintEasyRead(testCase.block).some((p) => p.level === 'error');
  if (!caught) {
    selfTestBad++;
    fail(`self-test: ${testCase.expect}`, 'the linter did not catch this defective entry');
  }
}

if (!selfTestBad) {
  console.log(`  ${green('ok')}   ${dim(`linter catches all ${cases.length} defective fixtures`)}`);
}

// ── PASS 4 · QUALITY ──────────────────────────────────────────────────────────

console.log('\nQUALITY');

const seenIds = new Map();
const seenText = new Map();
let qualityBad = 0;

for (const block of blocks) {
  if (seenIds.has(block.id)) {
    qualityBad++;
    fail(block.id, `duplicate id, also in ${seenIds.get(block.id)}`);
  }
  seenIds.set(block.id, block.id);

  const key = block.canonical_text.trim().toLowerCase();
  if (seenText.has(key)) {
    qualityBad++;
    fail(block.id, `duplicate phrase text, same as ${seenText.get(key)}`);
  }
  seenText.set(key, block.id);
}

// Unresolved symbol labels are a warning, not a failure: a phrase with fewer
// pictographs still works, and blocking the corpus on one missing picture would
// be the wrong trade.
for (const category of rawCategories) {
  for (const entry of category.entries) {
    const missing = unknownLabels(entry.symbols ?? []);
    if (missing.length) {
      warn(`phrase.${category.slug}.${entry.id}: no symbol for ${missing.map((m) => `"${m}"`).join(', ')}`);
    }
  }
}

const withSymbols = blocks.filter((b) => b.representations.pictographs?.length).length;
const withPhonemes = blocks.filter((b) => b.representations.phonemes).length;
const withIsl = blocks.filter((b) => b.representations.isl_clip).length;

const difficulty = [1, 2, 3, 4, 5].map(
  (level) => blocks.filter((b) => b.difficulty === level).length,
);

if (!qualityBad) console.log(`  ${green('ok')}   ${dim('no duplicate ids or phrases')}`);

// ── PASS 5 · COVERAGE ─────────────────────────────────────────────────────────

console.log('\nCOVERAGE');
console.log(`  ${'category'.padEnd(30)} ${'have'.padStart(5)} ${'target'.padStart(7)}`);
console.log(`  ${'-'.repeat(30)} ${'-'.repeat(5)} ${'-'.repeat(7)}`);

for (const category of categories) {
  const short = category.actual < category.target;
  const line = `  ${category.title.padEnd(30)} ${String(category.actual).padStart(5)} ${String(category.target).padStart(7)}`;
  console.log(short ? yellow(line) : line);
}

console.log(`  ${'-'.repeat(30)} ${'-'.repeat(5)} ${'-'.repeat(7)}`);
console.log(`  ${'TOTAL'.padEnd(30)} ${String(blocks.length).padStart(5)} ${String(TARGET_TOTAL).padStart(7)}`);

console.log('');
console.log(`  difficulty 1-5      ${difficulty.join(' / ')}`);
// Notes are conditional: a report that still says "pending" after the work is
// done teaches the team to stop reading it.
const note = (have, pending) => (have === blocks.length ? green('complete') : dim(pending));

console.log(`  with pictographs    ${withSymbols}/${blocks.length}   ${note(withSymbols, '(symbol mapping incomplete)')}`);
console.log(`  with phonemes       ${withPhonemes}/${blocks.length}   ${note(withPhonemes, '(run services/speech: python -m scripts.generate_phonemes --write)')}`);
console.log(`  with ISL clips      ${withIsl}/${blocks.length}   ${note(withIsl, '(recording sessions pending — needs a Deaf signer)')}`);

// ── RESULT ────────────────────────────────────────────────────────────────────

if (warnings.length) {
  console.log(`\nWARNINGS (${warnings.length})`);
  for (const warning of warnings.slice(0, 15)) console.log(`  ${yellow('warn')} ${warning}`);
  if (warnings.length > 15) console.log(`  ${dim(`… and ${warnings.length - 15} more`)}`);
}

console.log('');
if (failures) {
  console.log(red(`${failures} content violation${failures === 1 ? '' : 's'}\n`));
  process.exit(1);
}
console.log(green(`content bank valid — ${blocks.length} phrases, all reachable by all five personas\n`));

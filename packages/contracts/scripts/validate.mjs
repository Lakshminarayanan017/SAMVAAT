#!/usr/bin/env node
/**
 * Contract validation — the CI gate behind "accessibility as architecture".
 *
 * Three passes:
 *   1. SCHEMA         fixtures in valid/ must validate; fixtures in invalid/ must be rejected
 *   2. ACCESSIBILITY  every valid ContentBlock must satisfy the A11Y rules below
 *   3. GATE SELF-TEST fixtures in inaccessible/ are schema-valid but must FAIL an A11Y rule
 *
 * Pass 2 is the one that matters. Schema validation only proves a block is
 * well-formed; the A11Y rules prove it is *reachable by every persona*. That is
 * what makes it structurally impossible to author content excluding someone
 * (ADR-0001, Ethics E7).
 *
 * Pass 3 exists because a gate nobody tests is a gate that silently stops working.
 */
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { buildValidator, formatErrors, FIXTURE_DIR, ROOT_SCHEMAS } from './schema-registry.mjs';

const ajv = buildValidator();
let failures = 0;
let checks = 0;

const red = (s) => `\x1b[31m${s}\x1b[0m`;
const green = (s) => `\x1b[32m${s}\x1b[0m`;
const dim = (s) => `\x1b[2m${s}\x1b[0m`;

function fail(what, detail) {
  failures++;
  console.log(`  ${red('FAIL')} ${what}`);
  if (detail) console.log(detail);
}
function pass(what) {
  checks++;
  console.log(`  ${green('ok')}   ${dim(what)}`);
}

/** Fixtures carry `_comment` explaining their purpose; it is not part of the contract. */
function readFixture(path) {
  const data = JSON.parse(readFileSync(path, 'utf8'));
  for (const key of Object.keys(data)) if (key.startsWith('_')) delete data[key];
  return data;
}

function jsonFiles(dir) {
  return existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith('.json')).sort() : [];
}

// ── A11Y RULES ────────────────────────────────────────────────────────────────
// Each rule names the persona it protects. A rule protecting nobody in
// docs/PERSONAS.md does not belong here.

const A11Y_RULES = [
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
      return t
        .split(/\n|(?<=[.!?])\s+/)
        .filter((s) => s.trim())
        .every((s) => s.trim().split(/\s+/).length <= 15);
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
function a11yViolations(block) {
  return A11Y_RULES.filter((r) => !r.check(block)).map((r) => r.id);
}

function reportA11y(block, label) {
  const broken = A11Y_RULES.filter((r) => !r.check(block));
  for (const rule of broken) {
    fail(`${label} → ${rule.id}`,
      `      ${rule.message}\n      ${dim(`protects ${rule.persona}: ${rule.why}`)}`);
  }
  return broken.length === 0;
}

// ── PASS 1 · SCHEMA ───────────────────────────────────────────────────────────

console.log('\nSCHEMA');

for (const schemaFile of ROOT_SCHEMAS) {
  const validate = ajv.getSchema(schemaFile);
  if (!validate) {
    fail(`${schemaFile} did not compile`);
    continue;
  }
  const name = schemaFile.replace('.schema.json', '');

  for (const [dir, shouldPass] of [['valid', true], ['invalid', false], ['inaccessible', true]]) {
    const path = join(FIXTURE_DIR, dir, name);
    for (const file of jsonFiles(path)) {
      const valid = validate(readFixture(join(path, file)));
      const label = `${dir}/${name}/${file}`;

      if (valid === shouldPass) {
        pass(label + (shouldPass ? '' : ' correctly rejected'));
      } else if (shouldPass) {
        fail(label, formatErrors(validate.errors));
      } else {
        fail(label, '      expected this fixture to be REJECTED, but it validated');
      }
    }
  }
}

// ── PASS 2 · ACCESSIBILITY ────────────────────────────────────────────────────

console.log('\nACCESSIBILITY');

const validBlocks = join(FIXTURE_DIR, 'valid', 'content-block');
for (const file of jsonFiles(validBlocks)) {
  const block = readFixture(join(validBlocks, file));
  checks++;
  if (reportA11y(block, block.id)) pass(`${block.id} reachable by all five personas`);
}

// Content authored in packages/content is held to exactly the same rules.
const contentDir = join(FIXTURE_DIR, '..', '..', 'content', 'phrases');
if (existsSync(contentDir)) {
  const validate = ajv.getSchema('content-block.schema.json');
  for (const file of jsonFiles(contentDir)) {
    const parsed = JSON.parse(readFileSync(join(contentDir, file), 'utf8'));
    for (const block of Array.isArray(parsed) ? parsed : [parsed]) {
      checks++;
      if (!validate(block)) fail(`content/${block.id ?? file}`, formatErrors(validate.errors));
      else if (reportA11y(block, `content/${block.id}`)) pass(`content/${block.id}`);
    }
  }
}

// ── PASS 3 · GATE SELF-TEST ───────────────────────────────────────────────────
// These fixtures are schema-valid but deliberately exclude a persona. If the gate
// stops catching them, the gate is broken — and we would never otherwise notice.

console.log('\nGATE SELF-TEST');

const inaccessible = join(FIXTURE_DIR, 'inaccessible', 'content-block');
for (const file of jsonFiles(inaccessible)) {
  const block = readFixture(join(inaccessible, file));
  const broken = a11yViolations(block);
  checks++;
  if (broken.length) pass(`${block.id} correctly caught by ${broken.join(', ')}`);
  else fail(`inaccessible/${file}`, '      expected an A11Y violation, but the gate passed it');
}

// ── RESULT ────────────────────────────────────────────────────────────────────

console.log('');
if (failures) {
  console.log(red(`${failures} contract violation${failures === 1 ? '' : 's'} across ${checks} checks\n`));
  process.exit(1);
}
console.log(green(`${checks} checks passed — contracts and accessibility rules hold\n`));

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
import { A11Y_RULES, a11yViolations, brokenRules } from './a11y-rules.mjs';

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

// ── A11Y REPORTING ────────────────────────────────────────────────────────────
// The rules themselves live in a11y-rules.mjs so the content build enforces the
// identical set. Two copies would drift, and the drift would appear as content
// that passes one gate and excludes a learner anyway.

function reportA11y(block, label) {
  const broken = brokenRules(block);
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

// The Workplace Language Bank is validated in depth by its own build
// (`npm run content:validate`), which runs these same rules plus the Easy-Read
// linter and a coverage report. Here we only confirm the built output is
// schema-valid, so a stale or hand-edited dist cannot slip through.
const builtBlocks = join(FIXTURE_DIR, '..', '..', 'content', 'dist', 'blocks.json');
if (existsSync(builtBlocks)) {
  const validate = ajv.getSchema('content-block.schema.json');
  const blocks = JSON.parse(readFileSync(builtBlocks, 'utf8'));
  let bad = 0;

  for (const block of blocks) {
    if (!validate(block)) {
      bad++;
      fail(`content/${block.id ?? '(no id)'}`, formatErrors(validate.errors));
    } else if (brokenRules(block).length) {
      bad++;
      reportA11y(block, `content/${block.id}`);
    }
  }

  checks++;
  if (!bad) pass(`content bank: ${blocks.length} blocks schema-valid and accessible`);
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

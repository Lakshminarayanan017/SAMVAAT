#!/usr/bin/env node
/**
 * Fails if the committed generated code no longer matches the schemas.
 *
 * Generated output is committed so that consumers do not need the toolchain to
 * build. That only stays honest if CI checks it, hence this script.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { GENERATED_DIR } from './schema-registry.mjs';

const files = ['types.ts', 'models.py'];
const before = Object.fromEntries(files.map((f) => [f, read(join(GENERATED_DIR, f))]));

execFileSync(process.execPath, ['scripts/generate-typescript.mjs'], { stdio: 'ignore' });
execFileSync(process.execPath, ['scripts/generate-python.mjs'], { stdio: 'ignore' });

const drifted = files.filter((f) => read(join(GENERATED_DIR, f)) !== before[f]);

function read(p) {
  try { return readFileSync(p, 'utf8'); } catch { return null; }
}

if (drifted.length) {
  console.error(
    `\n\x1b[31mGenerated code is out of date:\x1b[0m ${drifted.join(', ')}\n` +
    `Run \x1b[1mnpm run contracts:build\x1b[0m and commit the result.\n`
  );
  process.exit(1);
}

console.log('generated code matches the schemas');

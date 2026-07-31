#!/usr/bin/env node
/**
 * JSON Schema -> TypeScript.
 *
 * Output is committed to `generated/` and CI asserts it has not drifted
 * (`npm run contracts:check`). Never hand-edit the generated file - change the
 * schema and re-run `npm run contracts:build`.
 *
 * Shared definitions live in common.schema.json and are referenced by all three
 * root schemas. They are emitted exactly once, up front; the root schemas are
 * then compiled with `declareExternallyReferenced: false` so they reference
 * those names rather than re-declaring them (which would not compile).
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { compile } from 'json-schema-to-typescript';
import { SCHEMA_DIR, GENERATED_DIR, ROOT_SCHEMAS, loadSchema } from './schema-registry.mjs';

const BANNER = `/**
 * GENERATED FILE - DO NOT EDIT.
 *
 * Source of truth: packages/contracts/schemas/*.schema.json
 * Regenerate with: npm run contracts:build
 */

/* eslint-disable */
`;

const baseOptions = {
  cwd: SCHEMA_DIR,
  bannerComment: '',
  additionalProperties: false,
  style: { singleQuote: true, semi: true, printWidth: 100 },
  unknownAny: false,
};

const parts = [BANNER];
const common = loadSchema('common.schema.json');

// ── Shared definitions, emitted once ─────────────────────────────────────────
// Wrap every $def in a synthetic object so the compiler is forced to declare
// each one, then drop the wrapper interface from the output.

const wrapper = {
  $id: 'common.schema.json',
  title: '__CommonWrapper',
  type: 'object',
  additionalProperties: false,
  required: Object.keys(common.$defs),
  properties: Object.fromEntries(
    Object.keys(common.$defs).map((name) => [name, { $ref: `#/$defs/${name}` }]),
  ),
  $defs: common.$defs,
};

const commonTs = await compile(wrapper, '__CommonWrapper', {
  ...baseOptions,
  declareExternallyReferenced: true,
});

parts.push(
  '// ── Shared definitions (common.schema.json) ─────────────────────────',
  '',
  stripDeclaration(commonTs, '__CommonWrapper').trim(),
  '',
);

// Literal-union types are more useful with a runtime array beside them, for
// exhaustiveness checks and for iterating channels in the Modality Router.
const constArrays = Object.entries(common.$defs)
  .filter(([, def]) => Array.isArray(def.enum))
  .map(([name, def]) =>
    `export const ${screamingSnake(name)}_VALUES: readonly ${name}[] = [` +
    `${def.enum.map((v) => `'${v}'`).join(', ')}] as const;`,
  );

parts.push(constArrays.join('\n'), '');

// ── Root contracts ───────────────────────────────────────────────────────────

parts.push('// ── Contracts ───────────────────────────────────────────────────────', '');

for (const file of ROOT_SCHEMAS) {
  const schema = loadSchema(file);
  const ts = await compile(schema, schema.title, {
    ...baseOptions,
    declareExternallyReferenced: false,
  });
  parts.push(ts.trim(), '');
}

/** Remove the synthetic wrapper interface, keeping every other declaration. */
function stripDeclaration(source, name) {
  const pattern = new RegExp(
    `(?:\\/\\*\\*[\\s\\S]*?\\*\\/\\s*)?export interface ${name} \\{[\\s\\S]*?\\n\\}\\n?`,
    'g',
  );
  return source.replace(pattern, '');
}

function screamingSnake(name) {
  return name.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toUpperCase();
}

mkdirSync(GENERATED_DIR, { recursive: true });
const out = join(GENERATED_DIR, 'types.ts');
writeFileSync(out, parts.join('\n'), 'utf8');

console.log(`generated  ${out}`);

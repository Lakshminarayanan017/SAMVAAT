/**
 * Shared schema loading for every script in this package.
 *
 * All schemas live in `schemas/` and reference each other by bare filename
 * (e.g. `common.schema.json#/$defs/InputMode`). Registering each schema under
 * its own `$id` is what makes those relative refs resolve in Ajv.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const here = dirname(fileURLToPath(import.meta.url));

export const SCHEMA_DIR = join(here, '..', 'schemas');
export const FIXTURE_DIR = join(here, '..', 'fixtures');
export const GENERATED_DIR = join(here, '..', 'generated');

/** Contracts that get types generated. `common` is refs-only, so it is excluded. */
export const ROOT_SCHEMAS = [
  'content-block.schema.json',
  'learner-response.schema.json',
  'communication-ability-profile.schema.json',
];

export function schemaFiles() {
  return readdirSync(SCHEMA_DIR).filter((f) => f.endsWith('.schema.json')).sort();
}

export function loadSchema(file) {
  return JSON.parse(readFileSync(join(SCHEMA_DIR, file), 'utf8'));
}

/** An Ajv instance with every schema registered, ready to validate any contract. */
export function buildValidator() {
  const ajv = new Ajv({ allErrors: true, strict: false, useDefaults: false });
  addFormats(ajv);
  for (const file of schemaFiles()) {
    ajv.addSchema(loadSchema(file), file);
  }
  return ajv;
}

/** Human-readable Ajv errors. Contract failures should be obvious, not decoded. */
export function formatErrors(errors) {
  if (!errors?.length) return '';
  return errors
    .map((e) => `      ${e.instancePath || '(root)'} ${e.message}` +
      (e.params?.allowedValues ? ` [${e.params.allowedValues.join(', ')}]` : '') +
      (e.params?.additionalProperty ? ` '${e.params.additionalProperty}'` : ''))
    .join('\n');
}

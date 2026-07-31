#!/usr/bin/env node
/**
 * JSON Schema → Pydantic v2 models.
 *
 * Written in-house rather than using `datamodel-code-generator` so that the
 * Node build stays self-contained — a Python tool in the JS build pipeline is a
 * cross-ecosystem dependency that breaks on someone's machine every few weeks.
 *
 * Handles the subset our schemas actually use: $defs enums, objects, $ref,
 * arrays, unions of primitives, defaults and required/optional. If a schema ever
 * needs more than that, extend this file — do not hand-edit the output.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { GENERATED_DIR, ROOT_SCHEMAS, loadSchema } from './schema-registry.mjs';

const PRIMITIVES = { string: 'str', integer: 'int', number: 'float', boolean: 'bool', 'null': 'None' };

const common = loadSchema('common.schema.json');
const emitted = new Set();
const blocks = [];

/** Resolve `common.schema.json#/$defs/Foo` → { name: 'Foo', def }. */
function resolveRef(ref) {
  const [file, pointer] = ref.split('#');
  const schema = file && file !== '' ? loadSchema(file) : common;
  const name = pointer.split('/').pop();
  return { name, def: schema.$defs[name] };
}

function pyType(schema, hint) {
  if (!schema) return 'Any';

  if (schema.$ref) {
    const { name, def } = resolveRef(schema.$ref);
    emitDef(name, def);
    return name;
  }
  // Inline enums become Literal[...] so Python enforces the same members the
  // JSON Schema does. Never assume `str` here - `{"type":"integer","enum":[1,2]}`
  // is a real shape in our schemas.
  if (Array.isArray(schema.enum)) {
    return `Literal[${schema.enum.map((v) => JSON.stringify(v)).join(', ')}]`;
  }
  if (Array.isArray(schema.type)) {
    const inner = schema.type.filter((t) => t !== 'null').map((t) => PRIMITIVES[t] ?? 'Any');
    const u = inner.length > 1 ? `Union[${inner.join(', ')}]` : inner[0];
    return schema.type.includes('null') ? `Optional[${u}]` : u;
  }
  if (schema.type === 'array') return `list[${pyType(schema.items, hint)}]`;
  if (schema.type === 'object') {
    if (schema.properties) return emitInline(hint, schema);
    return 'dict[str, Any]';
  }
  return PRIMITIVES[schema.type] ?? 'Any';
}

function fieldArgs(schema, required) {
  const args = [];
  if (required) args.push('...');
  else if (schema.default !== undefined) args.push(JSON.stringify(schema.default).replace(/^true$/, 'True').replace(/^false$/, 'False'));
  else args.push('None');

  if (schema.description) args.push(`description=${JSON.stringify(schema.description)}`);
  if (schema.minimum !== undefined) args.push(`ge=${schema.minimum}`);
  if (schema.maximum !== undefined) args.push(`le=${schema.maximum}`);
  if (schema.minLength !== undefined) args.push(`min_length=${schema.minLength}`);
  if (schema.minItems !== undefined) args.push(`min_length=${schema.minItems}`);
  // Deliberately NOT a Python raw string: JSON.stringify already escapes
  // backslashes, and r"\\." would match a literal backslash rather than a dot.
  if (schema.pattern !== undefined) args.push(`pattern=${JSON.stringify(schema.pattern)}`);
  return args.join(', ');
}

function emitModel(name, schema) {
  if (emitted.has(name)) return name;
  emitted.add(name);

  const required = new Set(schema.required ?? []);
  const lines = [`class ${name}(BaseModel):`];
  if (schema.description) lines.push(`    """${wrap(schema.description)}"""`, '');
  lines.push('    model_config = ConfigDict(extra="forbid")', '');

  const props = Object.entries(schema.properties ?? {});
  if (!props.length) lines.push('    pass');

  for (const [prop, sub] of props) {
    const isReq = required.has(prop);
    let t = pyType(sub, `${name}${pascal(prop)}`);
    if (!isReq && !t.startsWith('Optional[')) t = `Optional[${t}]`;
    lines.push(`    ${prop}: ${t} = Field(${fieldArgs(sub, isReq)})`);
  }

  blocks.push(lines.join('\n'));
  return name;
}

function emitInline(name, schema) {
  return emitModel(name, schema);
}

function emitDef(name, def) {
  if (emitted.has(name)) return;
  if (Array.isArray(def.enum)) {
    emitted.add(name);
    const doc = def.description ? `    """${wrap(def.description)}"""\n\n` : '';
    const members = def.enum.map((v) => `    ${String(v).toUpperCase()} = ${JSON.stringify(v)}`).join('\n');
    blocks.push(`class ${name}(str, Enum):\n${doc}${members}`);
    return;
  }
  if (def.type === 'object') { emitModel(name, def); return; }
  // Scalar aliases such as Difficulty stay inline as their primitive type.
  emitted.add(name);
  blocks.push(`${name} = ${PRIMITIVES[def.type] ?? 'Any'}` +
    (def.description ? `\n"""${wrap(def.description)}"""` : ''));
}

const pascal = (s) => s.replace(/(^|_)([a-z0-9])/g, (_, __, c) => c.toUpperCase());
const wrap = (s) => s.replace(/\s+/g, ' ').trim();

for (const file of ROOT_SCHEMAS) {
  const schema = loadSchema(file);
  emitModel(schema.title, schema);
}

const header = `"""
GENERATED FILE - DO NOT EDIT.

Source of truth: packages/contracts/schemas/*.schema.json
Regenerate with: npm run contracts:build
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

`;

mkdirSync(GENERATED_DIR, { recursive: true });
const out = join(GENERATED_DIR, 'models.py');
writeFileSync(out, header + blocks.join('\n\n\n') + '\n', 'utf8');

console.log(`generated  ${out}`);

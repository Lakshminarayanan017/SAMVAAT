/**
 * Proves the Modality Router boundary is actually enforced.
 *
 * The ESLint rule in eslint.config.js is the enforcement mechanism, but a rule
 * nobody tests is a rule that silently stops working — the same reason the
 * contracts package ships a gate self-test.
 *
 * This runs ESLint over a deliberately non-compliant snippet and asserts the
 * violation is reported.
 */
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { ESLint } from 'eslint';

const scratch = mkdtempSync(join(tmpdir(), 'samvaad-boundary-'));

afterAll(() => rmSync(scratch, { recursive: true, force: true }));

async function lint(code: string, filename: string) {
  const file = join(process.cwd(), 'src', 'features', '__boundary_probe__', filename);
  writeFileSync(join(scratch, filename), code, 'utf8');

  const eslint = new ESLint({ cwd: process.cwd() });
  const [result] = await eslint.lintText(code, { filePath: file });
  return result?.messages ?? [];
}

// Each case runs a real ESLint pass over a scratch file. That is the point —
// a mocked linter would prove nothing about the rule that actually ships — but
// it costs seconds, not milliseconds, and grows with the config.
const LINT_TIMEOUT_MS = 30_000;

describe('the Modality Router boundary', { timeout: LINT_TIMEOUT_MS }, () => {
  it('rejects a feature importing a renderer directly', async () => {
    const messages = await lint(
      `import { EasyReadRenderer } from '@/modality/renderers/EasyReadRenderer';\nexport default EasyReadRenderer;\n`,
      'bad-renderer-import.ts',
    );

    const violation = messages.find((m) => m.ruleId === 'no-restricted-imports');
    expect(violation, 'expected the boundary rule to fire').toBeDefined();
    expect(violation?.message).toMatch(/Do not import a renderer directly/);
  });

  it('rejects a feature reaching into the registry', async () => {
    const messages = await lint(
      `import { getRenderer } from '@/modality/registry';\nexport default getRenderer;\n`,
      'bad-registry-import.ts',
    );

    expect(
      messages.some((m) => m.ruleId === 'no-restricted-imports'),
      'expected the registry to be off-limits to feature code',
    ).toBe(true);
  });

  it('allows the supported import', async () => {
    const messages = await lint(
      `import { ModalityRouter } from '@/modality';\nexport default ModalityRouter;\n`,
      'good-import.ts',
    );

    expect(messages.filter((m) => m.ruleId === 'no-restricted-imports')).toHaveLength(0);
  });
});

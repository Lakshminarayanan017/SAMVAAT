/**
 * axe-core, wired for jsdom.
 *
 * Automated tooling catches roughly 30% of real accessibility problems. This is
 * the cheap 30% — it will never replace the manual screen-reader, keyboard and
 * switch-access passes in docs/ACCESSIBILITY.md, and nobody should read a green
 * axe run as "this is accessible".
 *
 * What it is very good at is catching regressions: an unlabelled control or a
 * broken heading order introduced six months from now, in a component nobody
 * thought to re-test by hand.
 */
import axe, { type AxeResults, type RunOptions } from 'axe-core';

/**
 * Rules that cannot produce a trustworthy result under jsdom, and where that
 * coverage is provided elsewhere. Each entry needs a reason — an unexplained
 * disabled rule is how an audit quietly stops auditing.
 */
const JSDOM_UNSUPPORTED: Record<string, string> = {
  // jsdom implements no layout or cascade, so every element computes as
  // transparent-on-transparent and the rule reports meaningless results.
  // Covered instead by tests/design-system/tokens.test.ts, which proves every
  // pair in all four themes against the WCAG maths directly.
  'color-contrast': 'jsdom has no layout engine; covered by the token contrast suite',
};

export interface AxeCheckOptions {
  /** Extra rules to disable for this call. Each must be justified in the test. */
  disable?: string[];
}

export async function checkA11y(
  container: Element,
  options: AxeCheckOptions = {},
): Promise<AxeResults> {
  const disabled = [...Object.keys(JSDOM_UNSUPPORTED), ...(options.disable ?? [])];

  const runOptions: RunOptions = {
    // WCAG 2.2 AA is our conformance target (docs/ACCESSIBILITY.md).
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] },
    rules: Object.fromEntries(disabled.map((rule) => [rule, { enabled: false }])),
    resultTypes: ['violations'],
  };

  return axe.run(container, runOptions);
}

/** A readable failure message. A raw axe dump is unreadable in CI output. */
export function formatViolations(results: AxeResults): string {
  if (!results.violations.length) return '';

  return results.violations
    .map((violation) => {
      const nodes = violation.nodes
        .map((node) => `      ${node.html}\n        ${node.failureSummary ?? ''}`)
        .join('\n');
      return `  [${violation.impact}] ${violation.id}: ${violation.help}\n${nodes}`;
    })
    .join('\n\n');
}

/** Only critical and serious block a merge; minor findings are logged, not gating. */
export function blockingViolations(results: AxeResults) {
  return results.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious',
  );
}

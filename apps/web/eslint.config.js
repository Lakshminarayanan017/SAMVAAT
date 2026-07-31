// @ts-check
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

/**
 * The rule that matters is the last one.
 *
 * Everything else here is ordinary hygiene. The `no-restricted-imports` block
 * at the bottom is the mechanism that makes "accessibility as architecture"
 * hold over time: feature code physically cannot reach a renderer, so it cannot
 * choose how content is presented, so it cannot present content in a way a
 * learner is unable to use.
 *
 * Without this rule the Modality Router is a convention, and conventions decay.
 * With it, bypassing the router fails the build.
 */
export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', '**/*.config.js'] },

  eslint.configs.recommended,
  ...tseslint.configs.recommended,

  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
      eqeqeq: ['error', 'always'],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },

  // ── The Modality Router boundary ──────────────────────────────────────────
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/modality/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/modality/renderers/*', '@/modality/renderers/*'],
              message:
                'Do not import a renderer directly. Render <ModalityRouter block={…} /> and let ' +
                "the learner's Communication Ability Profile choose the presentation. " +
                'See docs/ADR/0001-modality-neutral-content.md.',
            },
            {
              group: ['**/modality/input/adapters/*', '@/modality/input/adapters/*'],
              message:
                'Do not import an input adapter directly. Render <ModalityInput block={…} /> and ' +
                "let the learner's profile choose how they answer. " +
                'See docs/ADR/0002-canonical-text-response.md.',
            },
            {
              group: [
                '**/modality/registry',
                '@/modality/registry',
                '**/modality/input/registry',
                '@/modality/input/registry',
              ],
              message:
                'The registries are internal to the modality layer. Import { ModalityRouter, ' +
                "ModalityInput } from '@/modality' instead.",
            },
          ],
        },
      ],
    },
  },

  // Tests may reach into the modality internals: verifying the registry and the
  // fallback chain is precisely their job.
  {
    files: ['tests/**/*.{ts,tsx}'],
    rules: { 'no-restricted-imports': 'off', 'no-console': 'off' },
  },
);

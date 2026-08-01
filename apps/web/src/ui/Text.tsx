/**
 * Text — type that is never set inline.
 *
 * THE EASY-READ MECHANISM
 * -----------------------
 * The important thing this primitive does is make Easy-Read a *global switch*
 * rather than a branch in every screen.
 *
 * Without it, every component that renders text has to ask "is this learner on
 * Easy-Read?" and pick a size and line height. Ten screens asking that question
 * is ten chances to forget, and the learner who is forgotten is the one who
 * cannot read the result.
 *
 * With it, `variant` names a role — `body`, `title`, `caption` — and the
 * mapping from role to actual type changes once, here, when Easy-Read is on.
 * A screen cannot forget because a screen never knew.
 *
 * `caption` deliberately does not shrink under Easy-Read. Small supporting text
 * is exactly what an Easy-Read reader most needs kept legible, and "captions are
 * small" is a convention rather than a requirement.
 */
import type { CSSProperties, ElementType, ReactNode } from 'react';

import { useProfile } from '@/a11y/ProfileProvider';

import { mergeStyles } from './styles';

export type TextVariant = 'display' | 'title' | 'heading' | 'body' | 'caption';
export type TextTone = 'primary' | 'secondary' | 'success' | 'attention' | 'on-interactive';

interface TypeSpec {
  fontSize: string;
  lineHeight: string;
  fontWeight: string;
}

const STANDARD: Record<TextVariant, TypeSpec> = {
  display: { fontSize: '2.25rem', lineHeight: '1.35', fontWeight: '700' },
  title: { fontSize: '1.75rem', lineHeight: '1.35', fontWeight: '700' },
  heading: { fontSize: '1.375rem', lineHeight: '1.35', fontWeight: '600' },
  body: { fontSize: '1.125rem', lineHeight: '1.6', fontWeight: '400' },
  caption: { fontSize: '1rem', lineHeight: '1.6', fontWeight: '400' },
};

/**
 * Easy-Read: larger, looser, and with a smaller range between levels.
 *
 * A big spread between heading and body helps a fluent reader skim. An
 * Easy-Read reader is not skimming, and a 2.25rem display followed by 1rem
 * captions is two very different reading experiences on one screen.
 */
const EASY_READ: Record<TextVariant, TypeSpec> = {
  display: { fontSize: '2rem', lineHeight: '1.4', fontWeight: '700' },
  title: { fontSize: '1.625rem', lineHeight: '1.4', fontWeight: '700' },
  heading: { fontSize: '1.375rem', lineHeight: '1.5', fontWeight: '600' },
  body: { fontSize: '1.25rem', lineHeight: '1.8', fontWeight: '400' },
  caption: { fontSize: '1.125rem', lineHeight: '1.8', fontWeight: '400' },
};

const TONE: Record<TextTone, string> = {
  primary: 'var(--text-primary)',
  secondary: 'var(--text-secondary)',
  success: 'var(--success-ink)',
  attention: 'var(--attention-ink)',
  'on-interactive': 'var(--text-on-interactive)',
};

const DEFAULT_ELEMENT: Record<TextVariant, ElementType> = {
  display: 'h1',
  title: 'h2',
  heading: 'h3',
  body: 'p',
  caption: 'p',
};

export interface TextProps {
  variant?: TextVariant;
  tone?: TextTone;
  /**
   * Override the element without changing the type.
   *
   * Needed because heading *level* is a document-structure decision and type
   * *size* is a visual one. A screen whose second section happens to need
   * smaller type must not therefore skip from h2 to h4.
   */
  as?: ElementType;
  /** Caps line length. Prose beyond ~66 characters is measurably harder to track. */
  measure?: boolean;
  style?: CSSProperties;
  children: ReactNode;
}

export function Text({
  variant = 'body',
  tone = 'primary',
  as,
  measure = false,
  style,
  children,
  ...rest
}: TextProps & Record<string, unknown>) {
  const { profile } = useProfile();
  const easyRead = profile.text_complexity === 'easy_read';
  const spec = (easyRead ? EASY_READ : STANDARD)[variant];
  const Component = as ?? DEFAULT_ELEMENT[variant];

  return (
    <Component
      {...rest}
      data-ui="text"
      data-variant={variant}
      style={mergeStyles(
        {
          margin: 0,
          color: TONE[tone],
          ...spec,
        },
        measure ? { maxInlineSize: easyRead ? '52ch' : '66ch' } : undefined,
        style,
      )}
    >
      {children}
    </Component>
  );
}

/**
 * Button.
 *
 * Four variants, and the interesting decisions are about what a variant is
 * *not* allowed to be.
 *
 * `quiet` still draws a border. The usual "tertiary" button is borderless and
 * reveals itself on hover — which makes it invisible to a switch user, who
 * never hovers, and to a screen-magnifier user who cannot see the hover target
 * and the label at the same time.
 *
 * `danger` is not red-on-white. Colour is never the only signal (§9.1), so a
 * destructive button carries a heavier border *and* its label always names what
 * will be destroyed. "Delete" is not an acceptable label; "Delete everything
 * about me" is.
 *
 * There is no `size="small"`. Every button is at least `--target-min`, which
 * the learner's profile can raise to 88px. A small variant would be a
 * documented way to defeat that.
 */
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

import { interactiveBase, mergeStyles } from './styles';

export type ButtonVariant = 'primary' | 'secondary' | 'quiet' | 'danger';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  variant?: ButtonVariant;
  /** Stretches to the width of its container. */
  block?: boolean;
  /**
   * Shows a busy state and disables activation.
   *
   * The label is replaced by `loadingLabel` rather than being hidden behind a
   * spinner, because a spinner alone tells a screen-reader user nothing about
   * what is happening or how long it might take.
   */
  loading?: boolean;
  loadingLabel?: string;
  /** Set when the button sits on a card, so the focus ring's inner tone matches. */
  onRaised?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'secondary',
    block = false,
    loading = false,
    loadingLabel = 'Working…',
    onRaised = false,
    disabled,
    style,
    children,
    type = 'button',
    ...rest
  },
  ref,
) {
  return (
    <button
      {...rest}
      ref={ref}
      type={type}
      data-ui="button"
      data-variant={variant}
      data-on-raised={onRaised ? 'true' : undefined}
      disabled={disabled || loading}
      // Announced rather than merely visual: a learner who cannot see the
      // button change state still hears that it is busy.
      aria-busy={loading || undefined}
      style={mergeStyles(
        interactiveBase,
        block ? { inlineSize: '100%' } : undefined,
        style,
      )}
    >
      {loading ? loadingLabel : children}
    </button>
  );
});

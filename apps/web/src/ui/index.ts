/**
 * The primitive layer (Blueprint §9.5).
 *
 * Feature code imports from here and nowhere deeper. That single rule is what
 * keeps the presentation layer consistent as it grows: a screen that cannot
 * reach a raw token cannot invent its own spacing scale, its own button, or its
 * own idea of what "muted text" means.
 *
 * WHAT IS DELIBERATELY ABSENT
 * ---------------------------
 * There is no `<Spacer>`, no `size="small"`, and no `variant="link"`. Each is a
 * documented way to defeat something the design system guarantees — a spacer
 * bypasses the spacing scale, a small button bypasses the learner's target-size
 * setting, and a link-styled button is a control that only announces itself on
 * hover, which excludes every switch user.
 */
export { Button, type ButtonProps, type ButtonVariant } from './Button';
export { Card, ActionCard, type CardProps, type ActionCardProps } from './Card';
export { Stack, Grid, type StackProps } from './Stack';
export { Text, type TextProps, type TextVariant, type TextTone } from './Text';
export { ProgressDots, ProgressBar, type ProgressDotsProps, type ProgressBarProps } from './Progress';
export { Field, type FieldProps } from './Field';
export { Dialog, Sheet, type OverlayProps } from './Dialog';
export {
  Skeleton,
  ErrorState,
  EmptyState,
  Icon,
  type SkeletonProps,
  type StateProps,
  type IconProps,
} from './Feedback';
export { GAP, mergeStyles, type Gap } from './styles';

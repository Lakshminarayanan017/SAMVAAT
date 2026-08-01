/**
 * Motion.
 *
 * The product has to feel alive, and every learner has to be able to turn that
 * off completely. Those are not in tension — they are the same requirement,
 * because motion that carries meaning cannot be turned off, so no motion here
 * ever carries meaning.
 *
 * THE RULE THAT MAKES THIS SAFE
 * -----------------------------
 * Animation may only ever *emphasise* something that is already true in the
 * DOM. A star that appears is announced; the animation makes it feel earned. A
 * level that unlocks is readable as text; the animation draws the eye. Remove
 * every animation in this file and the app is still completely usable and says
 * exactly the same things — that is the test, and `tests/design-system` runs it.
 *
 * REDUCED MOTION IS NOT "SLOWER"
 * ------------------------------
 * `prefers-reduced-motion` means vestibular-safe, not sedate. Scale, spin,
 * parallax and large translation are the triggers; opacity and colour are not.
 * So reduced mode keeps cross-fades — which preserve the sense that something
 * happened — and drops everything that moves through space.
 *
 * Vestibular disorders are common, and a celebration that makes somebody
 * nauseous is a celebration that closes the app.
 */

export type MotionPreference = 'full' | 'reduced';

/**
 * Durations, in milliseconds.
 *
 * Short. The ceiling anywhere in the product is 420ms, because a learner using
 * switch scanning waits for every animation to finish before the next scan step
 * is safe to read, and a 900ms celebration costs them real time on every single
 * item.
 */
export const DURATION = {
  /** Hover, press, focus. Must feel instant. */
  instant: 90,
  /** Tile state changes, tooltips, small reveals. */
  quick: 160,
  /** Panel and screen transitions. */
  base: 240,
  /** Celebrations. The only place this long is justified. */
  celebrate: 420,
} as const;

/**
 * Easing curves.
 *
 * `spring` is a cubic approximation rather than a real spring: a physics spring
 * has no fixed duration, and an animation whose end nobody can predict is one a
 * screen reader announcement cannot be synchronised with.
 */
export const EASING = {
  /** Entering the screen. Decelerates — arrives and settles. */
  enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Leaving. Accelerates — gets out of the way. */
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
  /** Both ends. The default for anything that moves and stays. */
  standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
  /** A single controlled overshoot. Rewards only. */
  spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const;

/** Read the OS preference. */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Resolve the effective preference.
 *
 * The learner's own setting wins over the OS, in both directions. Somebody who
 * has turned reduced motion on system-wide for a different app must still be
 * able to turn animation back on here, and vice versa — an OS setting is a
 * default, not a verdict.
 */
export function resolveMotion(profileReduced: boolean | undefined): MotionPreference {
  if (profileReduced === true) return 'reduced';
  if (profileReduced === false) return 'full';
  return prefersReducedMotion() ? 'reduced' : 'full';
}

export interface TransitionOptions {
  duration?: number;
  easing?: string;
  delay?: number;
}

/**
 * Build a `transition` value that collapses safely under reduced motion.
 *
 * Reduced mode returns a short opacity-only transition rather than `none`. A
 * hard cut loses the signal that something changed, and for a learner with a
 * cognitive disability that signal is doing real work — the change simply must
 * not travel through space to deliver it.
 */
export function transition(
  properties: string[],
  motion: MotionPreference,
  options: TransitionOptions = {},
): string {
  const { duration = DURATION.base, easing = EASING.standard, delay = 0 } = options;

  if (motion === 'reduced') {
    return `opacity ${DURATION.quick}ms ${EASING.standard} ${delay}ms`;
  }

  return properties
    .map((property) => `${property} ${duration}ms ${easing} ${delay}ms`)
    .join(', ');
}

/**
 * Stagger delays for a list that animates in.
 *
 * Capped, and the cap is the point: ten world tiles at 40ms each is a pleasant
 * 400ms cascade, fifty level tiles would be two seconds of a learner watching
 * content they asked for arrive slowly. Anything past the cap appears with the
 * last staggered item.
 */
export function stagger(index: number, motion: MotionPreference, step = 40, cap = 8): number {
  if (motion === 'reduced') return 0;
  return Math.min(index, cap) * step;
}

/**
 * The keyframe name for a named effect, or `none` under reduced motion.
 *
 * Keyframes live in `styles/motion.css` so they can be defined once and reused,
 * rather than being re-declared inline by every component that wants a pop.
 */
export function keyframe(
  name: 'pop' | 'rise' | 'shimmer' | 'pulse' | 'fade-in' | 'star-land',
  motion: MotionPreference,
): string {
  if (motion === 'reduced') {
    // Fade survives. It is the one effect with no vestibular risk, and it keeps
    // the "something happened" signal that the reveal depends on.
    return name === 'fade-in' ? 'samvaad-fade-in' : 'none';
  }
  return `samvaad-${name}`;
}

/**
 * Frames a celebration is allowed to last, as a promise the caller can await.
 *
 * Returned as a promise so a caller can sequence an announcement after the
 * animation without hard-coding the duration in two places and letting them
 * drift.
 */
export function celebrationDuration(motion: MotionPreference): number {
  return motion === 'reduced' ? DURATION.quick : DURATION.celebrate;
}

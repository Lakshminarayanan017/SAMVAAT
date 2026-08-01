/**
 * Stars.
 *
 * Three of them, and what they mean matters more than how they look:
 *
 *     ★     you finished the level
 *     ★★    every phrase has been right at least once
 *     ★★★   every phrase has stuck
 *
 * The third cannot be earned in one sitting by anybody, however able. It is
 * earned by coming back — the one measure a fluent speaker has no advantage at.
 *
 * ACCESSIBILITY
 * -------------
 * The count is text first. `<span class="visually-hidden">` carries the real
 * sentence, the icons are `aria-hidden`, and an unearned star is an OUTLINE
 * rather than a faded fill — opacity alone vanishes in forced-colours mode and
 * is unreliable at high contrast, so a learner would see three identical stars
 * and no way to tell which they had.
 */
import { VISUALLY_HIDDEN } from '@/a11y/Announcer';
import { keyframe, stagger, type MotionPreference } from '@/design-system/motion';

const STAR_PATH =
  'M12 2.6l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5-5.8-3-5.8 3 1.1-6.5L2.6 9.4l6.5-.9z';

export interface StarsProps {
  earned: number;
  total?: number;
  size?: number;
  motion?: MotionPreference;
  /** Animate them landing. Only when a star was just won. */
  celebrate?: boolean;
}

export function Stars({
  earned,
  total = 3,
  size = 20,
  motion = 'full',
  celebrate = false,
}: StarsProps) {
  return (
    <span className="stars" data-testid="stars">
      <span style={VISUALLY_HIDDEN}>{describe(earned, total)}</span>

      {Array.from({ length: total }, (_, index) => {
        const isEarned = index < earned;

        return (
          <svg
            key={index}
            className="stars__icon"
            data-earned={isEarned}
            width={size}
            height={size}
            viewBox="0 0 24 24"
            aria-hidden="true"
            style={
              celebrate && isEarned
                ? {
                    animation: `${keyframe('star-land', motion)} 420ms both`,
                    // Landing one after another reads as counting up, which is
                    // the feeling. All three at once reads as a state change.
                    animationDelay: `${stagger(index, motion, 130)}ms`,
                  }
                : undefined
            }
          >
            <path d={STAR_PATH} />
          </svg>
        );
      })}
    </span>
  );
}

/**
 * A star total, as a count rather than as icons.
 *
 * A world holds up to twelve stars. Drawing twelve outlines is unreadable at a
 * glance, unreadable at 400% zoom, and takes a screen reader twelve steps to
 * cross. One icon and a number says the same thing in one step.
 */
export function StarCount({
  earned,
  max,
  size = 18,
}: {
  earned: number;
  max: number;
  size?: number;
}) {
  return (
    <span className="stars" data-testid="star-count">
      <span style={VISUALLY_HIDDEN}>
        {earned} of {max} stars in this world.
      </span>

      <svg
        className="stars__icon"
        data-earned={earned > 0}
        width={size}
        height={size}
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path d={STAR_PATH} />
      </svg>

      <span aria-hidden="true" style={{ fontWeight: 700, fontSize: '0.95rem' }}>
        {earned}/{max}
      </span>
    </span>
  );
}

/**
 * The sentence a screen reader hears.
 *
 * "3 of 3" is accurate and flat. Naming what the last star means is the part
 * worth hearing, because it is the only place the product explains that mastery
 * is measured by returning rather than by performing.
 */
function describe(earned: number, total: number): string {
  if (earned === 0) return `No stars yet, out of ${total}.`;
  if (earned >= total) return `All ${total} stars. These have stuck.`;
  if (earned === 1) return `1 star of ${total}. Finished.`;
  return `${earned} stars of ${total}. Come back to make them stick.`;
}

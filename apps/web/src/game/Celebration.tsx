/**
 * The celebration (Blueprint §10.5, ADR-0010).
 *
 * The payoff moment, and the one place in the product where 420ms is justified.
 *
 * TWO THINGS THAT ARE EASY TO GET WRONG
 * -------------------------------------
 * 1. **It is announced ONCE, as a complete sentence, after the animation.**
 *    The obvious implementation fires a live-region update per element — stars,
 *    then XP, then the badge — which a screen reader reads as three
 *    interruptions, the last two cutting off the first. What a learner should
 *    hear is "Level finished. Two stars. Forty XP." in one utterance.
 *
 * 2. **The celebration is at the end of the unit of work, not per mission.**
 *    Celebrating every correct answer devalues the currency and lengthens the
 *    session by roughly 40%. This component is rendered once, by the runner,
 *    when a level ends.
 *
 * THREE MOTION LEVELS
 * -------------------
 * Full gets a bounded particle burst — ≤24, single emission, no loop. Gentle
 * (the default) lands the stars with a stagger and no particles. Still
 * cross-fades. `prefers-reduced-motion` forces Still unless the learner has
 * said otherwise in-app.
 *
 * Remove every animation here and the screen still says exactly the same
 * things. That is the rule, and `tests/game/Celebration.test.tsx` checks it.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';
import { DURATION, type MotionPreference } from '@/design-system/motion';
import { Button, Card, Stack, Text } from '@/ui';

export type CelebrationLevel = 'full' | 'gentle' | 'still';

/** ≤24, single emission, no loop, no full-screen coverage (ADR-0010). */
const MAX_PARTICLES = 24;

/** Stars land one after another — counting up, not a state change. */
const STAR_STAGGER_MS = 130;

export interface CelebrationProps {
  starsEarned: number;
  starsPossible?: number;
  xpEarned: number;
  /** Awarded this session, if any. Each carries its own text label. */
  badges?: { id: string; label: string; earned_message: string }[];
  level: CelebrationLevel;
  onAgain: () => void;
  onDone: () => void;
}

/**
 * Resolve the effective celebration level.
 *
 * The OS preference is a default, not a verdict: somebody who set reduced
 * motion months ago for a different app must be able to turn animation back on
 * here, and somebody who never found the OS setting must still be safe.
 */
export function resolveCelebration(
  chosen: CelebrationLevel | undefined,
  motion: MotionPreference,
): CelebrationLevel {
  if (chosen) return chosen;
  return motion === 'reduced' ? 'still' : 'gentle';
}

export function Celebration({
  starsEarned,
  starsPossible = 3,
  xpEarned,
  badges = [],
  level,
  onAgain,
  onDone,
}: CelebrationProps) {
  const announce = useAnnounce();
  const [landed, setLanded] = useState(level === 'still' ? starsEarned : 0);
  const announced = useRef(false);

  // One sentence, built once. Read after the animation rather than during it.
  const sentence = useMemo(() => {
    const parts = [
      'Level finished.',
      `${starsEarned} of ${starsPossible} star${starsPossible === 1 ? '' : 's'}.`,
      `${xpEarned} XP.`,
      ...badges.map((badge) => badge.earned_message),
    ];
    return parts.join(' ');
  }, [starsEarned, starsPossible, xpEarned, badges]);

  useEffect(() => {
    if (level === 'still') {
      setLanded(starsEarned);
      return;
    }

    // Stars land one at a time. Under Still this loop never runs and they are
    // simply all present, which says the same thing without moving.
    const timers = Array.from({ length: starsEarned }, (_, index) =>
      setTimeout(() => setLanded((count) => Math.max(count, index + 1)), index * STAR_STAGGER_MS),
    );
    return () => timers.forEach(clearTimeout);
  }, [level, starsEarned]);

  useEffect(() => {
    if (announced.current) return;
    announced.current = true;

    const delay =
      level === 'still' ? 0 : starsEarned * STAR_STAGGER_MS + DURATION.quick;

    // Announced once, after the movement. Announcing during it competes with
    // the learner reading the screen.
    const timer = setTimeout(() => announce(sentence), delay);
    return () => clearTimeout(timer);
  }, [announce, sentence, level, starsEarned]);

  return (
    <Card padding="lg" elevation="floating">
      <Stack gap="md">
        <Text variant="title" as="h2">
          Level finished
        </Text>

        <Stars earned={starsEarned} possible={starsPossible} landed={landed} level={level} />

        {level === 'full' && starsEarned >= starsPossible && <Particles />}

        {/* Every figure is on screen as text. The animation emphasises what is
            already here; it never carries it. */}
        <Text variant="heading" as="p">
          {xpEarned} XP
        </Text>

        {badges.length > 0 && (
          <Stack gap="xs" as="ul" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {badges.map((badge) => (
              <li key={badge.id}>
                {/* Badge art alone excludes a learner who cannot see it, so
                    every badge carries a text label. */}
                <Text variant="body">{badge.earned_message}</Text>
              </li>
            ))}
          </Stack>
        )}

        {/* "Done for today" is equal weight, never smaller, never grey. A
            product for people with fatigue conditions that makes stopping feel
            like quitting is a product that punishes fatigue (§5.2). */}
        <Stack direction="horizontal" gap="sm">
          <Button variant="primary" onRaised onClick={onAgain}>
            One more
          </Button>
          <Button variant="secondary" onRaised onClick={onDone}>
            Done for today
          </Button>
        </Stack>
      </Stack>
    </Card>
  );
}

function Stars({
  earned,
  possible,
  landed,
  level,
}: {
  earned: number;
  possible: number;
  landed: number;
  level: CelebrationLevel;
}) {
  return (
    <div
      // One group with one name. Five separate star announcements would bury
      // the fact in noise.
      role="img"
      aria-label={`${earned} of ${possible} stars`}
      style={{ display: 'flex', gap: '0.5rem' }}
    >
      {Array.from({ length: possible }, (_, index) => {
        const isEarned = index < earned;
        const isVisible = index < landed;

        return (
          <span
            key={index}
            aria-hidden="true"
            data-star={isEarned ? 'earned' : 'empty'}
            style={{
              fontSize: '2.5rem',
              lineHeight: 1,
              color: isEarned ? 'var(--interactive-rest)' : 'var(--surface-sunken)',
              opacity: isEarned && !isVisible ? 0 : 1,
              transform:
                level === 'still' || !isEarned || isVisible ? 'none' : 'scale(0.6)',
              transition:
                level === 'still'
                  ? `opacity ${DURATION.quick}ms ease`
                  : `opacity ${DURATION.base}ms ease, transform ${DURATION.base}ms cubic-bezier(0.34, 1.56, 0.64, 1)`,
            }}
          >
            {isEarned ? '★' : '☆'}
          </span>
        );
      })}
    </div>
  );
}

/**
 * A single bounded burst. Full level only.
 *
 * Deliberately capped and deliberately not full-screen. Vestibular disorders
 * are common and under-declared, and a learner who reaches this without having
 * told us anything should still meet something survivable — which is why this
 * is opt-in rather than the default (ADR-0010).
 */
function Particles() {
  const particles = useMemo(
    () =>
      Array.from({ length: MAX_PARTICLES }, (_, index) => ({
        id: index,
        angle: (index / MAX_PARTICLES) * 360,
        distance: 40 + ((index * 37) % 50),
      })),
    [],
  );

  return (
    <div
      aria-hidden="true"
      data-testid="celebration-particles"
      style={{ position: 'relative', blockSize: 0, overflow: 'visible' }}
    >
      {particles.map((particle) => (
        <span
          key={particle.id}
          style={{
            position: 'absolute',
            insetInlineStart: '50%',
            insetBlockStart: 0,
            inlineSize: '0.5rem',
            blockSize: '0.5rem',
            borderRadius: '999px',
            background: 'var(--interactive-rest)',
            // transform and opacity only — 60fps on a mid-range Android is the
            // target, and animating width or top is what loses it.
            transform: `rotate(${particle.angle}deg) translateY(-${particle.distance}px)`,
            opacity: 0,
            animation: `samvaad-particle ${DURATION.celebrate}ms ease-out forwards`,
          }}
        />
      ))}
    </div>
  );
}

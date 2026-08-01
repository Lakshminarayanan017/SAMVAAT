/**
 * Mitra — the mascot.
 *
 * A common mynah. Sanskrit and Hindi for "friend", and the bird every Indian
 * household knows as the one that learns to talk. That is the whole brief in
 * one character: this is a product about finding your voice, in India, and the
 * mynah is the bird that does exactly that. An owl would be about wisdom, which
 * is not what anybody here needs help with.
 *
 * WHAT MITRA IS NOT ALLOWED TO DO
 * -------------------------------
 * **Never disappointed.** There is no sad mood, no crossed arms, no crying. A
 * mascot that looks let down turns a bad day into a small shaming, and our
 * learners get enough of that. The worst Mitra ever gets is `thinking`.
 *
 * **Never a substitute for text.** Every mood is decorative — `aria-hidden`
 * unless a caller passes a label — because a learner who cannot see Mitra must
 * lose nothing. The encouragement is in the copy beside the bird, always.
 *
 * **Never in the way.** Mitra does not block, does not animate on a loop, and
 * does not appear during an activity. Between activities only.
 *
 * Drawn as inline SVG rather than shipped as an image: it inherits `currentColor`
 * so it works in every theme including forced high contrast, it scales with no
 * second asset, and it costs no network request on a metered connection.
 */
import { useId } from 'react';

import { DURATION, EASING, type MotionPreference } from '@/design-system/motion';

export type MitraMood =
  /** Resting. The default between activities. */
  | 'calm'
  /** Something went well. One controlled hop, then still. */
  | 'delighted'
  /** Listening while the learner records. Head tilted. */
  | 'listening'
  /** Working something out. The most concerned Mitra ever looks. */
  | 'thinking'
  /** Waving. Used once, on the welcome screen. */
  | 'greeting';

export interface MitraProps {
  mood?: MitraMood;
  /** Pixel size. The bird is square. */
  size?: number;
  motion?: MotionPreference;
  /**
   * Only pass this when Mitra is the *only* carrier of some meaning — which
   * should be never. Left undefined, the bird is hidden from assistive tech,
   * which is correct for decoration.
   */
  label?: string;
}

export function Mitra({
  mood = 'calm',
  size = 96,
  motion = 'full',
  label,
}: MitraProps) {
  const gradientId = useId();
  const decorative = label === undefined;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      role={decorative ? 'presentation' : 'img'}
      aria-hidden={decorative || undefined}
      aria-label={label}
      data-testid="mitra"
      data-mood={mood}
      style={{
        // The whole bird animates as one object. Animating parts independently
        // reads as a puppet rather than a creature.
        animation:
          motion === 'reduced' || mood === 'calm'
            ? undefined
            : `${ANIMATION[mood]} ${DURATION.celebrate}ms ${EASING.spring} both`,
        overflow: 'visible',
      }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          {/* The mynah's real colouring: warm brown body, darker head. */}
          <stop offset="0%" stopColor="#4a3728" />
          <stop offset="55%" stopColor="#7a5a41" />
          <stop offset="100%" stopColor="#8d6b4f" />
        </linearGradient>
      </defs>

      {/* Body. One rounded teardrop — readable at 24px. */}
      <path
        d="M60 22c19 0 32 15 32 34 0 21-14 38-32 38s-32-17-32-38c0-19 13-34 32-34z"
        fill={`url(#${gradientId})`}
      />

      {/* Wing. A single stroke, so it stays legible when small. */}
      <path
        d="M76 52c8 6 10 18 6 28-5 11-14 15-14 15"
        fill="none"
        stroke="#3a2b20"
        strokeWidth="5"
        strokeLinecap="round"
        opacity="0.55"
      />

      {/* The mynah's signature yellow eye patch. The one unmistakable feature. */}
      <ellipse cx="44" cy="46" rx="13" ry="10" fill="#f5b301" />
      <ellipse cx="76" cy="46" rx="13" ry="10" fill="#f5b301" />

      {/* Eyes. Position is the entire mood system — nothing else moves. */}
      <circle cx={EYES[mood].left} cy={EYES[mood].y} r="5.5" fill="#1a1208" />
      <circle cx={EYES[mood].right} cy={EYES[mood].y} r="5.5" fill="#1a1208" />

      {/* Catchlights. Two dots of white are the difference between alive and taxidermy. */}
      <circle cx={EYES[mood].left + 2} cy={EYES[mood].y - 2} r="1.8" fill="#ffffff" />
      <circle cx={EYES[mood].right + 2} cy={EYES[mood].y - 2} r="1.8" fill="#ffffff" />

      {/* Beak. Open when delighted or greeting — Mitra is a talking bird. */}
      {OPEN_BEAK.has(mood) ? (
        <>
          <path d="M53 60l14 0-7 5z" fill="#f5b301" />
          <path d="M53 60l14 0-7-6z" fill="#ffc94d" />
        </>
      ) : (
        <path d="M53 59l14 0-7 7z" fill="#f5b301" />
      )}

      {/* Feet. Present so the bird is standing rather than floating. */}
      <path
        d="M50 94v8M50 102l-5 4M50 102l5 4M70 94v8M70 102l-5 4M70 102l5 4"
        stroke="#c58a2e"
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* Crest. Three feathers. Lifts when delighted, which is the only part of
          the body that changes shape between moods. */}
      <path
        d={mood === 'delighted' ? 'M52 24l4-14M60 22l1-16M68 24l5-13' : 'M54 25l2-10M60 23l1-11M66 25l3-9'}
        stroke="#3a2b20"
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/**
 * Mood is expressed almost entirely by eye position.
 *
 * Deliberately minimal. Faces built from many moving parts land in the uncanny
 * valley fast, and a character that reads as slightly wrong is worse company
 * than one that reads as simple.
 */
const EYES: Record<MitraMood, { left: number; right: number; y: number }> = {
  calm: { left: 44, right: 76, y: 46 },
  // Looking up and out. Reads as pleased without a smile, which birds lack.
  delighted: { left: 45, right: 77, y: 43 },
  // Both eyes toward the learner. Attention, not scrutiny.
  listening: { left: 46, right: 74, y: 46 },
  // Looking off and up. The universal "working it out".
  thinking: { left: 41, right: 73, y: 43 },
  greeting: { left: 45, right: 77, y: 45 },
};

const OPEN_BEAK = new Set<MitraMood>(['delighted', 'greeting']);

/**
 * One animation per mood, and each plays exactly once.
 *
 * No looping idle animation. A mascot that moves forever is a permanent
 * distraction on a screen somebody with an attention difficulty is trying to
 * read, and it cannot be ignored the way a still image can.
 */
const ANIMATION: Record<MitraMood, string> = {
  calm: 'none',
  delighted: 'samvaad-mitra-hop',
  listening: 'samvaad-mitra-tilt',
  thinking: 'samvaad-mitra-tilt',
  greeting: 'samvaad-mitra-wave',
};

/**
 * Mitra with something to say.
 *
 * The speech bubble is real text in the DOM and is what assistive technology
 * reads; the bird beside it stays decorative. That split is the whole point —
 * remove the illustration and the message is untouched.
 */
export function MitraSays({
  children,
  mood = 'calm',
  size = 72,
  motion = 'full',
  tone = 'neutral',
}: {
  children: React.ReactNode;
  mood?: MitraMood;
  size?: number;
  motion?: MotionPreference;
  /** `celebrate` warms the bubble. Colour is never the only signal. */
  tone?: 'neutral' | 'celebrate';
}) {
  return (
    <div className="mitra-says" data-tone={tone}>
      <Mitra mood={mood} size={size} motion={motion} />
      <p className="mitra-says__bubble" role={tone === 'celebrate' ? 'status' : undefined}>
        {children}
      </p>
    </div>
  );
}

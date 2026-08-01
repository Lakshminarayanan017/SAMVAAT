/**
 * The world map — the screen a learner opens the app to see.
 *
 * Ten worlds, each opening into chapters and levels. It has to do three things
 * at once: show where you are, make where you are feel earned, and make the
 * next step obvious enough that nobody has to decide anything.
 *
 * WHY THIS IS A LIST AND NOT A WINDING PATH
 * -----------------------------------------
 * The obvious design is Duolingo's snaking trail of nodes. It looks wonderful
 * and it is a genuinely poor fit here.
 *
 * A winding path encodes order in two-dimensional position, which means a
 * screen reader gets a sequence of buttons with no spatial information, switch
 * scanning has to traverse a layout that zig-zags, and at 400% zoom — which
 * WCAG 2.2 requires to reflow — the path either breaks or scrolls in two
 * directions. Every one of those hits a persona we exist for.
 *
 * A vertical list of worlds, each expanding into its levels, is the same
 * information: ordered, progressive, and it reflows, scans, and reads aloud
 * correctly with no special handling. The delight comes from the world identity,
 * the stars and the motion, none of which need a curve to work.
 *
 * A `[V2]` decorative path drawn *behind* an already-correct list is a fine
 * idea. Building the path first and retrofitting the accessibility is not.
 */
import { useCallback, useState } from 'react';

import { useAnnounce, VISUALLY_HIDDEN } from '@/a11y/Announcer';
import { ICON_PATHS, paletteFor, type WorldIcon } from '@/design-system/worlds';
import { keyframe, stagger, type MotionPreference } from '@/design-system/motion';
import { StarCount, Stars } from './Stars';

export interface JourneyLevel {
  level_id: string;
  title: string;
  missions: string[];
  status: 'complete' | 'in_progress' | 'recommended' | 'available_early';
  stars: number;
  coverage: number;
  retention: number;
  effort: number;
  caption: string;
}

export interface JourneyChapter {
  chapter_id: string;
  title: string;
  sensitive: boolean;
  levels: JourneyLevel[];
  stars: number;
  max_stars: number;
}

export interface JourneyWorld {
  world_id: string;
  order: number;
  title: string;
  subtitle: string;
  easy_read_title: string;
  why: string;
  colour: string;
  icon: string;
  flagship: boolean;
  is_current: boolean;
  caption: string;
  chapters: JourneyChapter[];
  stars: number;
  max_stars: number;
}

export interface Journey {
  worlds: JourneyWorld[];
  total_stars: number;
  max_stars: number;
  next_level_id: string | null;
  headline: string;
}

export interface WorldMapProps {
  journey: Journey;
  onOpenLevel: (levelId: string) => void;
  motion?: MotionPreference;
  /** Easy-Read profiles get the shorter world titles and no subtitles. */
  easyRead?: boolean;
  /** Dark theme picks the dark half of each world palette. */
  dark?: boolean;
}

export function WorldMap({
  journey,
  onOpenLevel,
  motion = 'full',
  easyRead = false,
  dark = false,
}: WorldMapProps) {
  const announce = useAnnounce();

  // The current world starts open. Everything else starts closed, so a learner
  // using a screen reader is not made to walk past fifty levels to reach the
  // one we are recommending.
  const [open, setOpen] = useState<string | null>(
    journey.worlds.find((world) => world.is_current)?.world_id ?? null,
  );

  const toggle = useCallback(
    (world: JourneyWorld) => {
      const opening = open !== world.world_id;
      setOpen(opening ? world.world_id : null);
      announce(
        opening
          ? `${world.title} opened. ${world.chapters.reduce((n, c) => n + c.levels.length, 0)} levels.`
          : `${world.title} closed.`,
      );
    },
    [open, announce],
  );

  return (
    <div className="world-map">
      <h1 className="world-map__headline">{journey.headline}</h1>

      <p style={VISUALLY_HIDDEN}>
        {journey.total_stars} stars out of {journey.max_stars} across{' '}
        {journey.worlds.length} worlds. Nothing here is locked — every world can be
        opened at any time.
      </p>

      <ol className="world-list">
        {journey.worlds.map((world, index) => (
          <li
            key={world.world_id}
            style={{
              animation: `${keyframe('rise', motion)} 240ms both`,
              animationDelay: `${stagger(index, motion)}ms`,
            }}
          >
            <WorldCard
              world={world}
              expanded={open === world.world_id}
              onToggle={() => toggle(world)}
              easyRead={easyRead}
              dark={dark}
            />

            {open === world.world_id && (
              <div
                id={`world-panel-${world.world_id}`}
                style={{ padding: 'var(--space-md, 1rem) 0 0 var(--space-md, 1rem)' }}
              >
                {world.chapters.map((chapter) => (
                  <ChapterBlock
                    key={chapter.chapter_id}
                    chapter={chapter}
                    onOpenLevel={onOpenLevel}
                    motion={motion}
                  />
                ))}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function WorldCard({
  world,
  expanded,
  onToggle,
  easyRead,
  dark,
}: {
  world: JourneyWorld;
  expanded: boolean;
  onToggle: () => void;
  easyRead: boolean;
  dark: boolean;
}) {
  const palette = paletteFor(world.colour);
  const icon = ICON_PATHS[world.icon as WorldIcon] ?? ICON_PATHS.path;

  return (
    <button
      type="button"
      className="world-card"
      data-current={world.is_current}
      data-testid={`world-${world.world_id}`}
      aria-expanded={expanded}
      aria-controls={`world-panel-${world.world_id}`}
      onClick={onToggle}
      style={
        {
          '--world-wash': dark ? palette.washDark : palette.wash,
          '--world-ink': dark ? palette.inkDark : palette.ink,
          '--world-accent': dark ? palette.accentDark : palette.accent,
        } as React.CSSProperties
      }
    >
      {/* Shape is the second identity signal, so the map still works with no
          colour at all. */}
      <svg
        className="world-card__icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d={icon} />
      </svg>

      <span>
        {/* "Now" is a word, not a colour. Colour never carries this alone. */}
        {world.is_current && <span className="world-card__badge">Now</span>}
        {world.flagship && !world.is_current && (
          <span className="world-card__badge">Only here</span>
        )}

        <span className="world-card__title">
          <span style={VISUALLY_HIDDEN}>World {world.order}: </span>
          {easyRead ? world.easy_read_title : world.title}
        </span>

        {!easyRead && <span className="world-card__caption">{world.subtitle}</span>}
        <span className="world-card__caption">{world.caption}</span>
      </span>

      <StarCount earned={world.stars} max={world.max_stars} />
    </button>
  );
}

function ChapterBlock({
  chapter,
  onOpenLevel,
  motion,
}: {
  chapter: JourneyChapter;
  onOpenLevel: (levelId: string) => void;
  motion: MotionPreference;
}) {
  return (
    <section className="chapter" aria-labelledby={`chapter-${chapter.chapter_id}`}>
      <h2 className="chapter__title" id={`chapter-${chapter.chapter_id}`}>
        {chapter.title}
        <span style={VISUALLY_HIDDEN}>
          . {chapter.stars} of {chapter.max_stars} stars.
        </span>
      </h2>

      {/* Disclosure content. A learner rehearsing this is rehearsing something
          that can cost them a job, so the exit is stated before they start. */}
      {chapter.sensitive && (
        <p className="level-tile__caption" data-testid="sensitive-notice">
          You can stop any of these at any point, and nothing is saved. If you would
          rather talk it through with a person, your trainer can help.
        </p>
      )}

      <ol className="level-list">
        {chapter.levels.map((level, index) => (
          <li key={level.level_id}>
            <LevelTile
              level={level}
              index={index + 1}
              onOpen={() => onOpenLevel(level.level_id)}
              motion={motion}
            />
          </li>
        ))}
      </ol>
    </section>
  );
}

function LevelTile({
  level,
  index,
  onOpen,
  motion,
}: {
  level: JourneyLevel;
  index: number;
  onOpen: () => void;
  motion: MotionPreference;
}) {
  return (
    <button
      type="button"
      className="level-tile"
      data-status={level.status}
      data-testid={`level-${level.level_id}`}
      onClick={onOpen}
    >
      <span className="level-tile__index" aria-hidden="true">
        {index}
      </span>

      <span>
        {/* Everything a screen reader needs, in the order it is useful: which
            level, what state, and only then the decoration. */}
        <span style={VISUALLY_HIDDEN}>{STATUS_LABEL[level.status]}. </span>

        <span className="level-tile__title">{level.title}</span>
        <span className="level-tile__caption">{level.caption}</span>

        <ul className="level-tile__missions" aria-label="What is in this level">
          {level.missions.map((mission) => (
            <li key={mission} className="mission-chip">
              {MISSION_LABEL[mission] ?? mission}
            </li>
          ))}
        </ul>
      </span>

      <Stars earned={level.stars} motion={motion} />
    </button>
  );
}

/**
 * Spoken status.
 *
 * `available_early` is the one that matters. It must read as an open door —
 * a padlock, or the word "locked", on a product built for disabled people
 * reads as "not for you".
 */
const STATUS_LABEL: Record<JourneyLevel['status'], string> = {
  complete: 'Finished',
  in_progress: 'Carry on',
  recommended: 'Next',
  available_early: 'Further on, and open',
};

/** Plain names for the mission types. The internal ids are not learner-facing. */
const MISSION_LABEL: Record<string, string> = {
  recognise: 'Match it',
  produce: 'Say it your way',
  choose_in_context: 'What fits here',
  order_the_steps: 'Put it in order',
  scenario: 'Live it',
  roleplay: 'Talk it through',
  interview: 'The real thing',
  boss: 'Show what you can do',
};

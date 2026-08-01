#!/usr/bin/env node
/**
 * Resolves the learning journey against the real phrase bank.
 *
 * Levels in `curriculum/worlds.json` name a category and a slice; they never
 * hard-list phrase ids. This resolves those slices into real block ids at build
 * time, which means a level cannot silently reference a phrase that was renamed
 * or deleted — it fails the build instead.
 *
 * That matters more than it looks. Hand-written id lists are exactly the kind of
 * data that rots quietly: the corpus changes, the curriculum keeps pointing at
 * ghosts, and a learner opens a level that renders nothing.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildAll } from './build.mjs';

const here = dirname(fileURLToPath(import.meta.url));
export const CURRICULUM_DIR = join(here, '..', 'curriculum');
export const DIST_DIR = join(here, '..', 'dist');

export function loadWorlds() {
  return JSON.parse(readFileSync(join(CURRICULUM_DIR, 'worlds.json'), 'utf8'));
}

export function loadProfiles() {
  return JSON.parse(readFileSync(join(CURRICULUM_DIR, 'profiles.json'), 'utf8'));
}

/**
 * Group the built blocks by the category slug their id carries.
 *
 * Derived from the block id rather than from a separate mapping, so there is
 * one source of truth for which phrase belongs where.
 */
export function blocksByCategory(blocks) {
  const grouped = new Map();

  for (const block of blocks) {
    // `phrase.<category>.<entry>` — the id shape the content build produces.
    const category = block.id.split('.')[1];
    if (!grouped.has(category)) grouped.set(category, []);
    grouped.get(category).push(block);
  }

  return grouped;
}

/** Expand one level's `source` slice into concrete block ids. */
export function resolveLevel(level, grouped, problems, path) {
  const { category, from = 0, count } = level.source ?? {};
  const available = grouped.get(category);

  if (!available) {
    problems.push(`${path}: no such phrase category '${category}'`);
    return [];
  }

  if (from >= available.length) {
    problems.push(
      `${path}: slice starts at ${from} but '${category}' has only ${available.length} phrases`,
    );
    return [];
  }

  const slice = available.slice(from, from + count);

  // A short slice is a warning rather than an error: a category can legitimately
  // shrink, and truncating is better than refusing to build the whole app.
  if (slice.length < count) {
    problems.push(
      `${path}: asked for ${count} phrases from '${category}' at ${from}, got ${slice.length} ` +
        `(warning — the level still builds, with fewer items)`,
    );
  }

  return slice.map((block) => block.id);
}

export function buildCurriculum() {
  const { blocks } = buildAll();
  const grouped = blocksByCategory(blocks);

  const source = loadWorlds();
  const profiles = loadProfiles();
  const problems = [];

  const missionTypes = new Set(Object.keys(source.mission_types));

  const worlds = source.worlds.map((world) => {
    const chapters = world.chapters.map((chapter) => {
      const levels = chapter.levels.map((level) => {
        const path = `${world.id}/${chapter.id}/${level.id}`;

        for (const mission of level.missions) {
          if (!missionTypes.has(mission)) {
            problems.push(`${path}: unknown mission type '${mission}'`);
          }
        }

        const blockIds = resolveLevel(level, grouped, problems, path);

        return {
          id: `${world.id}.${chapter.id}.${level.id}`,
          title: level.title,
          missions: level.missions,
          block_ids: blockIds,
          //: Effort is the sum of the mission efforts, and it is what XP is
          //: paid on. Paying on effort rather than on score is what stops the
          //: game rewarding being good at speaking.
          effort: level.missions.reduce(
            (total, mission) => total + (source.mission_types[mission]?.effort ?? 1),
            0,
          ),
        };
      });

      return {
        id: `${world.id}.${chapter.id}`,
        title: chapter.title,
        sensitive: chapter.sensitive ?? false,
        levels,
      };
    });

    return {
      id: world.id,
      order: world.order,
      title: world.title,
      subtitle: world.subtitle,
      easy_read_title: world.easy_read_title,
      why: world.why,
      colour: world.colour,
      icon: world.icon,
      flagship: world.flagship ?? false,
      chapters,
      //: Every phrase this world touches, deduplicated. The world map uses it
      //: for the mastery ring without walking three levels of nesting.
      block_ids: [
        ...new Set(chapters.flatMap((c) => c.levels.flatMap((l) => l.block_ids))),
      ],
    };
  });

  validateProfiles(profiles, worlds, problems);
  validateCoverage(worlds, blocks, problems);

  return { worlds, profiles, missionTypes: source.mission_types, problems };
}

function validateProfiles(profiles, worlds, problems) {
  const worldIds = new Set(worlds.map((world) => world.id));
  const strategyIds = new Set(Object.keys(profiles.strategies));
  const seen = new Set();

  for (const profile of profiles.profiles) {
    if (seen.has(profile.id)) problems.push(`duplicate profile id '${profile.id}'`);
    seen.add(profile.id);

    for (const strategy of profile.strategies ?? []) {
      if (!strategyIds.has(strategy)) {
        problems.push(`profile '${profile.id}' names unknown strategy '${strategy}'`);
      }
    }

    for (const worldId of profile.world_emphasis ?? []) {
      if (!worldIds.has(worldId)) {
        problems.push(`profile '${profile.id}' emphasises unknown world '${worldId}'`);
      }
    }

    // The rule from profiles.json: reordering and re-weighting, never removal.
    // A preset that could hide a world would be deciding what a disabled person
    // is allowed to learn, which is the exact harm this product refuses.
    if (profile.world_exclusion || profile.hidden_worlds) {
      problems.push(
        `profile '${profile.id}' tries to remove worlds. Presets may reorder and re-weight, ` +
          `never remove — see the principles in curriculum/profiles.json`,
      );
    }

    const weights = Object.values(profile.scoring_weights ?? {});
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    if (weights.length && Math.abs(total - 1) > 0.001) {
      problems.push(
        `profile '${profile.id}' scoring weights sum to ${total.toFixed(3)}, expected 1.000`,
      );
    }
  }
}

/**
 * Every phrase should be reachable from some level.
 *
 * A phrase nobody can ever meet is content we paid to author and nobody will
 * ever see. Reported as a warning with the count, because during authoring an
 * unreferenced phrase is normal.
 */
function validateCoverage(worlds, blocks, problems) {
  const reachable = new Set(worlds.flatMap((world) => world.block_ids));
  const orphans = blocks.filter((block) => !reachable.has(block.id));

  if (orphans.length) {
    problems.push(
      `warning — ${orphans.length} of ${blocks.length} phrases are not reachable from any level ` +
        `(first: ${orphans[0].id})`,
    );
  }
}

function main() {
  const { worlds, profiles, missionTypes, problems } = buildCurriculum();

  const errors = problems.filter((problem) => !problem.includes('warning'));
  const warnings = problems.filter((problem) => problem.includes('warning'));

  for (const warning of warnings) console.warn(`  warn  ${warning}`);
  for (const error of errors) console.error(`  ERROR ${error}`);

  if (errors.length) {
    console.error(`\n${errors.length} curriculum error(s)`);
    process.exit(1);
  }

  mkdirSync(DIST_DIR, { recursive: true });
  writeFileSync(
    join(DIST_DIR, 'curriculum.json'),
    JSON.stringify({ version: 1, worlds, mission_types: missionTypes }, null, 2),
    'utf8',
  );
  writeFileSync(
    join(DIST_DIR, 'profiles.json'),
    JSON.stringify(profiles, null, 2),
    'utf8',
  );

  const levels = worlds.flatMap((w) => w.chapters.flatMap((c) => c.levels));
  console.log(
    `built ${worlds.length} worlds, ${worlds.flatMap((w) => w.chapters).length} chapters, ` +
      `${levels.length} levels, ${profiles.profiles.length} profiles`,
  );
}

if (process.argv[1]?.endsWith('curriculum.mjs')) main();

/**
 * Bundle budget (Blueprint §18.1, F3).
 *
 * Our learners are explicitly on entry-level Android and metered data. A bundle
 * budget is therefore an accessibility requirement, not a performance nicety:
 * an app that takes forty seconds to open on a ₹8,000 phone is an app that
 * excludes the people it was built for just as effectively as a missing caption
 * would.
 *
 * Measured gzipped, because that is what actually crosses the network.
 *
 * Only the ENTRY chunk counts against the budget. Route chunks are downloaded
 * on demand, so a learner who never opens the trainer dashboard never pays for
 * it — which is the entire point of splitting, and counting them here would
 * penalise doing the right thing.
 */
import { gzipSync } from 'node:zlib';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

/** Blueprint §17 Phase 1: initial JS <= 120KB gzipped. */
const BUDGET_KB = 120;

/**
 * A route chunk this big means something un-splittable leaked into it — most
 * likely the phrase bank, which is meant to live in IndexedDB and has escaped
 * into the bundle before.
 */
const ROUTE_CHUNK_WARN_KB = 60;

const dist = join(process.cwd(), 'dist', 'assets');

let files;
try {
  files = readdirSync(dist).filter((name) => name.endsWith('.js'));
} catch {
  console.error(`No build found at ${dist}. Run \`npm run build\` first.`);
  process.exit(1);
}

const gzippedKb = (name) => gzipSync(readFileSync(join(dist, name))).length / 1024;

// Vite names the entry chunk `index-<hash>.js`. Everything else is either a
// lazily-imported route or a shared chunk pulled in by one.
const entries = files.filter((name) => /^index-[\w-]+\.js$/.test(name));

if (entries.length !== 1) {
  console.error(
    `Expected exactly one entry chunk, found ${entries.length}: ${entries.join(', ')}.\n` +
      `If the build output naming changed, this check is now measuring the wrong thing.`,
  );
  process.exit(1);
}

const entry = entries[0];
const entryKb = gzippedKb(entry);

const routes = files
  .filter((name) => name !== entry)
  .map((name) => ({ name, kb: gzippedKb(name) }))
  .sort((a, b) => b.kb - a.kb);

const total = entryKb + routes.reduce((sum, chunk) => sum + chunk.kb, 0);

console.log('bundle budget');
console.log(`  entry            ${entryKb.toFixed(1)} KB gz  (budget ${BUDGET_KB} KB)`);
console.log(`  route chunks     ${routes.length}, ${(total - entryKb).toFixed(1)} KB gz total`);
console.log(`  largest route    ${routes[0]?.name ?? '—'} ${routes[0]?.kb.toFixed(1) ?? 0} KB gz`);
console.log(`  everything       ${total.toFixed(1)} KB gz`);

let failed = false;

if (entryKb > BUDGET_KB) {
  console.error(
    `\nFAIL entry chunk is ${entryKb.toFixed(1)} KB gzipped, over the ${BUDGET_KB} KB budget.\n` +
      `     Something that should be lazily loaded is being imported eagerly. The usual\n` +
      `     cause is a route screen imported by name somewhere instead of via React.lazy.`,
  );
  failed = true;
}

for (const chunk of routes) {
  if (chunk.kb > ROUTE_CHUNK_WARN_KB) {
    console.error(
      `\nFAIL route chunk ${chunk.name} is ${chunk.kb.toFixed(1)} KB gzipped.\n` +
        `     A route chunk this large usually means the phrase bank has leaked back into\n` +
        `     the bundle. It belongs in IndexedDB, fetched and cached at runtime.`,
    );
    failed = true;
  }
}

if (failed) process.exit(1);

console.log('\nwithin budget');

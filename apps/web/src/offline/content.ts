/**
 * Getting the phrase bank to the learner (M15).
 *
 * It used to be imported directly, which inlined all 226 blocks into the
 * JavaScript bundle — around 270 kB before ISL clips and phoneme data grow it.
 * Handing that to someone on a metered connection before they have seen a
 * single lesson is exactly the wrong trade for the people this exists for.
 *
 * Now: cache first, network second, and the network step is a 40-byte version
 * check before any download. On a slow connection the difference between
 * checking and downloading is the difference between opening the app and
 * giving up on it.
 */
import type { ContentBlock } from '@samvaad/contracts';

import { contentVersion, loadContent, saveContent } from './db';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface ContentResult {
  blocks: ContentBlock[];
  /** Where they came from. Surfaced so the UI can be honest about it. */
  source: 'cache' | 'network' | 'unavailable';
  version: string | null;
}

/**
 * The phrase bank, from wherever it can be had.
 *
 * Order of preference:
 *   1. cache, if the server agrees it is current (one small request)
 *   2. network
 *   3. cache, even if possibly stale — a slightly old curriculum beats no app
 *   4. nothing, said plainly
 */
export async function getContent(): Promise<ContentResult> {
  const cached = await loadContent();
  const cachedVersion = await contentVersion();

  // 1 — is what we have still current? Cheap enough to always ask.
  if (cached.length > 0 && cachedVersion) {
    const current = await fetchVersion();
    if (current === null) {
      // Offline. What we have is what we have, and it is almost certainly fine.
      return { blocks: cached, source: 'cache', version: cachedVersion };
    }
    if (current === cachedVersion) {
      return { blocks: cached, source: 'cache', version: cachedVersion };
    }
  }

  // 2 — fetch it.
  const fetched = await fetchBlocks();
  if (fetched) {
    await saveContent(fetched.blocks, fetched.version);
    return { blocks: fetched.blocks, source: 'network', version: fetched.version };
  }

  // 3 — stale beats nothing. A learner practising last week's curriculum is
  // vastly better served than one staring at an error.
  if (cached.length > 0) {
    return { blocks: cached, source: 'cache', version: cachedVersion };
  }

  // 4 — genuinely nothing. The caller must say so rather than showing an
  // empty lesson list, which reads as "there is nothing to learn".
  return { blocks: [], source: 'unavailable', version: null };
}

async function fetchVersion(): Promise<string | null> {
  try {
    const response = await fetch(`${BASE_URL}/content/version`);
    if (!response.ok) return null;
    return ((await response.json()) as { version: string }).version;
  } catch {
    return null;
  }
}

async function fetchBlocks(): Promise<{ blocks: ContentBlock[]; version: string } | null> {
  try {
    const response = await fetch(`${BASE_URL}/content/blocks`);
    if (!response.ok) return null;
    const body = (await response.json()) as { version: string; blocks: ContentBlock[] };
    return { blocks: body.blocks, version: body.version };
  } catch {
    return null;
  }
}

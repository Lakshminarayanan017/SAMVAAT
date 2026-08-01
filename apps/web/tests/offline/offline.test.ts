/**
 * The offline layer.
 *
 * The outbox tests are the ones that matter. A learner with dysarthria may have
 * spent thirty seconds on one sentence; losing it because a train went into a
 * tunnel is unforgivable, and "we retried three times" is not a defence.
 */
import 'fake-indexeddb/auto';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ContentBlock } from '@samvaad/contracts';

import {
  acknowledge,
  closeDb,
  contentVersion,
  dueCards,
  enqueue,
  loadContent,
  outboxSize,
  pending,
  recordFailure,
  saveCards,
  saveContent,
} from '@/offline/db';
import { getContent } from '@/offline/content';
import { flush } from '@/offline/sync';

function block(id: string): ContentBlock {
  return {
    id,
    kind: 'phrase',
    canonical_text: `Phrase ${id}`,
    intent: 'greeting',
    difficulty: 1,
    representations: { caption: `Phrase ${id}`, easy_read: `Phrase ${id}.` },
    interaction: { accepted_input_modes: ['text'] },
    a11y: { requires_audio: false, requires_vision: false, requires_speech: false },
    version: 1,
  } as ContentBlock;
}

beforeEach(async () => {
  await closeDb();
  indexedDB.deleteDatabase('samvaad');
  await closeDb();
});

afterEach(() => vi.unstubAllGlobals());

// ── the outbox ───────────────────────────────────────────────────────────────

describe('the outbox', () => {
  it('keeps every answer, in the order it was given', async () => {
    await enqueue('review', { block_id: 'a', correct: true });
    await enqueue('review', { block_id: 'b', correct: false });
    await enqueue('review', { block_id: 'c', correct: true });

    const queue = await pending();
    expect(queue.map((entry) => entry.payload['block_id'])).toEqual(['a', 'b', 'c']);
  });

  it('never deduplicates two identical answers', async () => {
    /** Two identical reviews a minute apart are two real events. Collapsing
     *  them would quietly discard one of the learner's attempts. */
    await enqueue('review', { block_id: 'a', correct: true });
    await enqueue('review', { block_id: 'a', correct: true });

    expect(await outboxSize()).toBe(2);
  });

  it('keeps an entry after a failure rather than dropping it', async () => {
    const id = await enqueue('review', { block_id: 'a', correct: true });
    await recordFailure(id, 'network down');

    const [entry] = await pending();
    expect(entry?.attempts).toBe(1);
    expect(entry?.lastError).toBe('network down');
    expect(await outboxSize()).toBe(1);
  });

  it('has no give-up-after-N-attempts path at all', async () => {
    /** A learner's answer is not ours to discard because our retry policy ran
     *  out of patience. */
    const id = await enqueue('review', { block_id: 'a', correct: true });
    for (let attempt = 0; attempt < 50; attempt++) {
      await recordFailure(id, 'still down');
    }

    expect(await outboxSize()).toBe(1);
    expect((await pending())[0]?.attempts).toBe(50);
  });

  it('only removes an entry once it is acknowledged', async () => {
    const id = await enqueue('review', { block_id: 'a', correct: true });
    expect(await outboxSize()).toBe(1);

    await acknowledge(id);
    expect(await outboxSize()).toBe(0);
  });
});

// ── replay ───────────────────────────────────────────────────────────────────

describe('replaying the outbox', () => {
  it('sends everything and clears it when the server accepts', async () => {
    await enqueue('review', { block_id: 'a', correct: true });
    await enqueue('review', { block_id: 'b', correct: true });

    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200 })));

    const result = await flush('tok');

    expect(result.sent).toBe(2);
    expect(result.remaining).toBe(0);
    expect(await outboxSize()).toBe(0);
  });

  it('sends in the order the answers were given', async () => {
    /** FSRS reconstructs a schedule from the sequence of grades. Out of order
     *  builds a history that never happened. */
    await enqueue('review', { block_id: 'first', correct: true });
    await enqueue('review', { block_id: 'second', correct: false });

    const seen: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_url: string, init: RequestInit) => {
        seen.push(JSON.parse(String(init.body)).block_id);
        return { ok: true, status: 200 };
      }),
    );

    await flush('tok');
    expect(seen).toEqual(['first', 'second']);
  });

  it('stops on a network failure and keeps the rest in order', async () => {
    await enqueue('review', { block_id: 'a', correct: true });
    await enqueue('review', { block_id: 'b', correct: true });
    await enqueue('review', { block_id: 'c', correct: true });

    let calls = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        calls += 1;
        if (calls === 2) throw new Error('offline');
        return { ok: true, status: 200 };
      }),
    );

    const result = await flush('tok');

    expect(result.interrupted).toBe(true);
    expect(result.sent).toBe(1);
    // b and c both survive, still in order.
    const remaining = await pending();
    expect(remaining.map((entry) => entry.payload['block_id'])).toEqual(['b', 'c']);
  });

  it('keeps an entry when the server is unwell', async () => {
    /** A 5xx is the server's problem, not the payload's. */
    await enqueue('review', { block_id: 'a', correct: true });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 503 })));

    const result = await flush('tok');

    expect(result.interrupted).toBe(true);
    expect(await outboxSize()).toBe(1);
  });

  it('drops a payload the server will never accept, loudly', async () => {
    /** Keeping a 4xx would loop forever. It goes, but a malformed payload is
     *  our bug and the log has to say so. */
    const error = vi.spyOn(console, 'error').mockImplementation(() => {});
    await enqueue('review', { block_id: 'nonsense', correct: true });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 422 })));

    const result = await flush('tok');

    expect(result.failed).toBe(1);
    expect(await outboxSize()).toBe(0);
    expect(error).toHaveBeenCalled();
    expect(String(error.mock.calls[0]?.[0])).toMatch(/client bug/i);
    error.mockRestore();
  });

  it('does nothing when there is nothing queued', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const result = await flush('tok');

    expect(result).toEqual({ sent: 0, failed: 0, remaining: 0, interrupted: false });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

// ── content cache ────────────────────────────────────────────────────────────

describe('the content cache', () => {
  it('stores and returns the phrase bank', async () => {
    await saveContent([block('a'), block('b')], 'v1');

    expect(await loadContent()).toHaveLength(2);
    expect(await contentVersion()).toBe('v1');
  });

  it('drops blocks the curriculum has retired', async () => {
    /** Otherwise a learner keeps practising something that no longer exists. */
    await saveContent([block('a'), block('b')], 'v1');
    await saveContent([block('a')], 'v2');

    const blocks = await loadContent();
    expect(blocks.map((entry) => entry.id)).toEqual(['a']);
  });

  it('serves from cache without downloading when the version matches', async () => {
    await saveContent([block('a')], 'v1');

    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => ({ version: 'v1' }),
      url,
    }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await getContent();

    expect(result.source).toBe('cache');
    // Only the cheap version check, never the payload.
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/content/version');
  });

  it('downloads when the server has something newer', async () => {
    await saveContent([block('old')], 'v1');

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        String(url).includes('/version')
          ? { ok: true, json: async () => ({ version: 'v2' }) }
          : { ok: true, json: async () => ({ version: 'v2', blocks: [block('new')] }) },
      ),
    );

    const result = await getContent();

    expect(result.source).toBe('network');
    expect(result.blocks.map((entry) => entry.id)).toEqual(['new']);
  });

  it('serves the cache when the network is gone', async () => {
    await saveContent([block('a')], 'v1');
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline'); }));

    const result = await getContent();

    expect(result.source).toBe('cache');
    expect(result.blocks).toHaveLength(1);
  });

  it('prefers a possibly stale cache over nothing at all', async () => {
    /** A learner practising last week's curriculum is vastly better served
     *  than one staring at an error. */
    await saveContent([block('a')], 'v1');
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        String(url).includes('/version')
          ? { ok: true, json: async () => ({ version: 'v9' }) }
          : { ok: false, status: 503 },
      ),
    );

    const result = await getContent();

    expect(result.source).toBe('cache');
    expect(result.blocks).toHaveLength(1);
  });

  it('says so plainly when there is genuinely nothing', async () => {
    /** An empty lesson list reads as "there is nothing to learn". */
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('offline'); }));

    const result = await getContent();

    expect(result.source).toBe('unavailable');
    expect(result.blocks).toEqual([]);
  });
});

// ── cards ────────────────────────────────────────────────────────────────────

describe('cached cards', () => {
  it('returns only what is due, most overdue first', async () => {
    const now = Date.now();
    await saveCards([
      { blockId: 'later', dueAt: now + 86_400_000, stability: 5, difficulty: 5, reps: 1, lapses: 0, lastReviewedAt: now },
      { blockId: 'overdue', dueAt: now - 86_400_000, stability: 5, difficulty: 5, reps: 1, lapses: 0, lastReviewedAt: now },
      { blockId: 'just-due', dueAt: now - 1000, stability: 5, difficulty: 5, reps: 1, lapses: 0, lastReviewedAt: now },
    ]);

    const due = await dueCards(now);
    expect(due.map((card) => card.blockId)).toEqual(['overdue', 'just-due']);
  });
});

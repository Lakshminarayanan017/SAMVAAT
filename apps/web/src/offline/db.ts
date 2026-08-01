/**
 * Local storage for offline practice (M15).
 *
 * The abstract's promise was "works where the learners actually are" — the
 * special schools, NGOs and NIEPMD-affiliated centres that need this most are
 * exactly where bandwidth is worst. This is the layer that keeps that promise.
 *
 * Four stores, and each one exists for a different reason:
 *
 *   content   the 226-phrase bank, fetched once. Moves ~270 kB out of the
 *             JavaScript bundle, which was the wrong thing to hand someone on
 *             a metered connection before they had seen a single lesson.
 *
 *   cards     scheduling state, so a session can be built with no network.
 *
 *   outbox    APPEND-ONLY. Every answer a learner gives while offline. This is
 *             the store that must never lose anything: someone with dysarthria
 *             may have spent thirty seconds on one sentence, and losing it
 *             because a train went into a tunnel is unforgivable.
 *
 *   meta      profile and sync bookkeeping.
 */
import { openDB, type DBSchema, type IDBPDatabase } from 'idb';

import type { CommunicationAbilityProfile, ContentBlock, LearnerResponse } from '@samvaad/contracts';

const DB_NAME = 'samvaad';
const DB_VERSION = 1;

export interface OutboxEntry {
  /** Auto-assigned. Also the send order — the outbox is a queue, not a set. */
  id?: number;
  kind: 'review' | 'response';
  /** Exactly what would have gone to the API. Replayed verbatim on reconnect. */
  payload: Record<string, unknown>;
  createdAt: number;
  /** Failed sends are counted, never silently dropped. */
  attempts: number;
  lastError?: string;
}

export interface CachedCard {
  blockId: string;
  dueAt: number;
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  lastReviewedAt: number | null;
}

interface SamvaadDb extends DBSchema {
  content: { key: string; value: ContentBlock };
  cards: { key: string; value: CachedCard };
  outbox: { key: number; value: OutboxEntry; indexes: { byCreatedAt: number } };
  meta: { key: string; value: unknown };
}

let database: Promise<IDBPDatabase<SamvaadDb>> | null = null;

export function db(): Promise<IDBPDatabase<SamvaadDb>> {
  database ??= openDB<SamvaadDb>(DB_NAME, DB_VERSION, {
    upgrade(instance) {
      if (!instance.objectStoreNames.contains('content')) {
        instance.createObjectStore('content', { keyPath: 'id' });
      }
      if (!instance.objectStoreNames.contains('cards')) {
        instance.createObjectStore('cards', { keyPath: 'blockId' });
      }
      if (!instance.objectStoreNames.contains('outbox')) {
        const outbox = instance.createObjectStore('outbox', {
          keyPath: 'id',
          autoIncrement: true,
        });
        // Replay order matters: a review recorded before another must be sent
        // before it, or FSRS reconstructs a history that never happened.
        outbox.createIndex('byCreatedAt', 'createdAt');
      }
      if (!instance.objectStoreNames.contains('meta')) {
        instance.createObjectStore('meta');
      }
    },
  });
  return database;
}

/** Test-only. Closes and forgets the connection. */
export async function closeDb(): Promise<void> {
  if (database) (await database).close();
  database = null;
}

// ── content ──────────────────────────────────────────────────────────────────

export async function saveContent(blocks: ContentBlock[], version: string): Promise<void> {
  const instance = await db();
  const tx = instance.transaction(['content', 'meta'], 'readwrite');

  // Cleared first: a block removed upstream must disappear here too, or a
  // learner keeps practising something the curriculum has retired.
  await tx.objectStore('content').clear();
  await Promise.all(blocks.map((block) => tx.objectStore('content').put(block)));
  await tx.objectStore('meta').put(version, 'contentVersion');
  await tx.done;
}

export async function loadContent(): Promise<ContentBlock[]> {
  return (await db()).getAll('content');
}

export async function contentVersion(): Promise<string | null> {
  return ((await db()).get('meta', 'contentVersion') as Promise<string | null>) ?? null;
}

// ── cards ────────────────────────────────────────────────────────────────────

export async function saveCards(cards: CachedCard[]): Promise<void> {
  const instance = await db();
  const tx = instance.transaction('cards', 'readwrite');
  await Promise.all(cards.map((card) => tx.store.put(card)));
  await tx.done;
}

export async function dueCards(now: number = Date.now()): Promise<CachedCard[]> {
  const cards = await (await db()).getAll('cards');
  return cards.filter((card) => card.dueAt <= now).sort((a, b) => a.dueAt - b.dueAt);
}

// ── outbox ───────────────────────────────────────────────────────────────────

/**
 * Record something the learner did. Never overwrites, never deduplicates.
 *
 * Two identical reviews a minute apart are two real events, and collapsing them
 * would quietly discard one of the learner's attempts.
 */
export async function enqueue(
  kind: OutboxEntry['kind'],
  payload: Record<string, unknown>,
): Promise<number> {
  return (await db()).add('outbox', {
    kind,
    payload,
    createdAt: Date.now(),
    attempts: 0,
  });
}

/** Everything waiting, oldest first. */
export async function pending(): Promise<OutboxEntry[]> {
  return (await db()).getAllFromIndex('outbox', 'byCreatedAt');
}

/** Remove an entry — ONLY after the server has confirmed it. */
export async function acknowledge(id: number): Promise<void> {
  await (await db()).delete('outbox', id);
}

/**
 * Record a failed attempt, keeping the entry.
 *
 * There is deliberately no "give up after N attempts" path. An entry that
 * cannot be sent stays in the outbox forever rather than being dropped: a
 * learner's answer is not ours to discard because our retry policy ran out of
 * patience. If something is genuinely unsendable that is a bug to fix, and the
 * evidence needs to still be there when we look.
 */
export async function recordFailure(id: number, error: string): Promise<void> {
  const instance = await db();
  const entry = await instance.get('outbox', id);
  if (!entry) return;

  await instance.put('outbox', {
    ...entry,
    attempts: entry.attempts + 1,
    lastError: error.slice(0, 200),
  });
}

export async function outboxSize(): Promise<number> {
  return (await db()).count('outbox');
}

// ── profile ──────────────────────────────────────────────────────────────────

export async function saveProfile(profile: CommunicationAbilityProfile): Promise<void> {
  await (await db()).put('meta', profile, 'profile');
}

export async function loadProfile(): Promise<CommunicationAbilityProfile | null> {
  return ((await db()).get('meta', 'profile') as Promise<CommunicationAbilityProfile | null>) ?? null;
}

export type { LearnerResponse };

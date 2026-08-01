/**
 * Getting offline work back to the server (M15).
 *
 * THE ONE RULE
 * ------------
 * Nothing leaves the outbox until the server has confirmed it. Not on a
 * timeout, not on a 500, not after N attempts. A learner with dysarthria may
 * have spent thirty seconds on one sentence; losing it because a train went
 * into a tunnel is unforgivable, and "we retried three times" is not a defence.
 *
 * The only thing that removes an entry is a 2xx — or a 4xx, which means the
 * server has definitively rejected it and retrying would loop forever. A 4xx is
 * logged loudly, because it is our bug, not the learner's.
 *
 * ORDER MATTERS
 * -------------
 * Reviews replay oldest first. FSRS reconstructs a schedule from the sequence
 * of grades, so sending them out of order builds a history that never happened.
 * One failure stops the run rather than skipping ahead.
 */
import { acknowledge, pending, recordFailure, type OutboxEntry } from './db';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

const ENDPOINTS: Record<OutboxEntry['kind'], string> = {
  review: '/practice/review',
  response: '/practice/review',
};

export interface SyncResult {
  sent: number;
  failed: number;
  remaining: number;
  /** True when the run stopped early — the network went away again. */
  interrupted: boolean;
}

/**
 * Replay everything waiting.
 *
 * Safe to call at any time: if nothing is queued it does nothing, and if it is
 * already running the caller simply gets the same work done twice, which is
 * harmless because acknowledgement is what removes an entry.
 */
export async function flush(token: string): Promise<SyncResult> {
  const queue = await pending();
  let sent = 0;
  let failed = 0;

  for (const entry of queue) {
    if (entry.id === undefined) continue;

    let response: Response | null = null;
    try {
      response = await fetch(`${BASE_URL}${ENDPOINTS[entry.kind]}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(entry.payload),
      });
    } catch (error) {
      // Network gone. Stop rather than burning through the queue recording
      // failures that all have the same cause — and, more importantly, so the
      // remaining entries keep their order for the next attempt.
      await recordFailure(entry.id, String(error));
      return { sent, failed: failed + 1, remaining: queue.length - sent, interrupted: true };
    }

    if (response.ok) {
      await acknowledge(entry.id);
      sent += 1;
      continue;
    }

    if (response.status >= 400 && response.status < 500) {
      // The server will never accept this. Keeping it would loop forever, so
      // it goes — but loudly, because a malformed payload is our bug.
      console.error(
        `[sync] server rejected a queued ${entry.kind} (${response.status}). ` +
          'This is a client bug: the payload was built wrong.',
        entry.payload,
      );
      await acknowledge(entry.id);
      failed += 1;
      continue;
    }

    // 5xx. The server is unwell, not the payload. Keep it and stop, so the
    // order survives for the retry.
    await recordFailure(entry.id, `HTTP ${response.status}`);
    return { sent, failed: failed + 1, remaining: queue.length - sent, interrupted: true };
  }

  return { sent, failed, remaining: 0, interrupted: false };
}

/**
 * Send when the network returns, and on a slow heartbeat.
 *
 * The heartbeat exists because `navigator.onLine` lies: it reports a network
 * interface, not reachability. A device on a captive portal or a hotel wifi
 * with no route out is "online" and cannot reach us. Rather than trust it, we
 * simply try periodically — the cost of a failed fetch every few minutes is
 * nothing compared to a learner's work sitting unsent.
 */
export function startSync(
  token: string,
  onResult?: (result: SyncResult) => void,
): () => void {
  const HEARTBEAT_MS = 60_000;

  const run = () => {
    void flush(token).then((result) => {
      if (result.sent > 0 || result.failed > 0) onResult?.(result);
    });
  };

  window.addEventListener('online', run);
  const timer = window.setInterval(run, HEARTBEAT_MS);

  // Also on load: the last session may have ended mid-queue.
  run();

  return () => {
    window.removeEventListener('online', run);
    window.clearInterval(timer);
  };
}

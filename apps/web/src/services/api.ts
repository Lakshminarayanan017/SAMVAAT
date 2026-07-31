/**
 * The API gateway client.
 *
 * Every call can fail — the gateway sits in front of two free-tier services and
 * a paid LLM. So this returns a discriminated result rather than throwing:
 * callers must handle the unavailable case, and the type system makes forgetting
 * impossible.
 *
 * A learner staring at a blank screen cannot tell "the service is down" from
 * "I did something wrong", and will assume the latter. Every failure therefore
 * carries a sentence written for them.
 */
import type { ContentBlock } from '@samvaad/contracts';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

/** Generous. LLM turns are slow; cutting one off gives a broken screen, not a fast one. */
const TURN_TIMEOUT_MS = 50_000;

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; message: string; status: number };

const FALLBACK_MESSAGE =
  'We could not reach that just now. Everything else still works — please try again in a moment.';

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = TURN_TIMEOUT_MS,
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...init.headers },
    });

    if (!response.ok) {
      // The gateway sends a learner-facing sentence in `detail.message`. Prefer
      // it over anything we could invent here — it knows which service failed.
      let message = FALLBACK_MESSAGE;
      try {
        const body = await response.json();
        if (typeof body?.detail?.message === 'string') message = body.detail.message;
      } catch {
        /* a non-JSON error body is still an outage; the fallback covers it */
      }
      return { ok: false, message, status: response.status };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === 'AbortError';
    return {
      ok: false,
      status: 0,
      message: aborted
        ? 'That is taking longer than usual. Please try again — nothing has been lost.'
        : FALLBACK_MESSAGE,
    };
  } finally {
    clearTimeout(timer);
  }
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) });

// ── interview ────────────────────────────────────────────────────────────────

export type InterviewTrack = 'hr' | 'role' | 'telephonic';
export type Persona = 'supportive' | 'neutral' | 'brisk';

export interface QuestionResponse {
  conversation_id: string;
  block: ContentBlock;
  generated: boolean;
  provider: string;
  finished: boolean;
  /** "Question 4 of about 10" — orientation, never a countdown (Ethics E6). */
  progress: string;
}

export interface ScoreResponse {
  scored: boolean;
  dimensions: { name: string; score: number; evidence?: string }[];
  strengths: string[];
  improvements: string[];
  unavailable_message: string;
  audit_id: string | null;
}

export const api = {
  startInterview: (
    userId: string,
    track: InterviewTrack,
    persona: Persona,
    jobContext: string,
  ) =>
    post<QuestionResponse>('/interview/start', {
      user_id: userId,
      track,
      persona,
      job_context: jobContext,
    }),

  answer: (conversationId: string, userId: string, answer: string | null) =>
    post<QuestionResponse>(`/interview/${conversationId}/answer`, {
      user_id: userId,
      answer,
    }),

  pauseInterview: (conversationId: string, userId: string) =>
    post<{ status: string; message: string }>(`/interview/${conversationId}/pause`, {
      user_id: userId,
    }),

  score: (userId: string, question: string, answer: string, roleContext = '') =>
    post<ScoreResponse>('/interview/score', {
      user_id: userId,
      question,
      answer,
      role_context: roleContext,
    }),

  // ── role-play ──────────────────────────────────────────────────────────────

  scenarios: () =>
    request<{ id: string; title: string; role: string; setting: string; goal: string }[]>(
      '/scenarios',
      {},
      10_000,
    ),

  startRoleplay: (userId: string, scenarioId: string, persona: Persona) =>
    post<{ conversation_id: string; block: ContentBlock; finished: boolean }>(
      '/roleplay/start',
      { user_id: userId, scenario_id: scenarioId, persona },
    ),

  reply: (conversationId: string, userId: string, text: string) =>
    post<{ conversation_id: string; block: ContentBlock; finished: boolean }>(
      `/roleplay/${conversationId}/reply`,
      { user_id: userId, text },
    ),
};

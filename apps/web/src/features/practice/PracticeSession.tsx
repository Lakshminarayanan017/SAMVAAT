/**
 * The daily practice loop (M4's client half).
 *
 * The screen a learner actually opens every day. Everything else in this
 * product exists to make this one worth returning to.
 *
 * FOUR THINGS IT WILL NOT DO
 * --------------------------
 * 1. **No timer, no countdown, no streak-at-risk.** The session shows how many
 *    items are left as orientation, never as pressure (Ethics E6).
 *
 * 2. **Never says "wrong".** The Charter's copy rules apply hardest here,
 *    because this is the string a learner reads most often. "Not quite yet" is
 *    the strongest negative the product owns.
 *
 * 3. **Never scores an unreliable transcription against the learner.** A
 *    low-confidence answer is confirmed with them, and the grade sent to the
 *    server says so — an ASR weakness must not surface as their weakness.
 *
 * 4. **Everything renders through the Modality Router.** A phrase is presented
 *    in whichever channels the learner's profile calls for, and answered
 *    through whichever they can use. The feature never picks.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ContentBlock, LearnerResponse } from '@samvaad/contracts';
import { CONFIDENCE_CONFIRM_THRESHOLD } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { useProfile } from '@/a11y/ProfileProvider';
import { ModalityInput, ModalityRouter } from '@/modality';
import { normaliseAnswer } from '@/features/practice/grading';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

interface SessionItem {
  block_id: string;
  canonical_text: string;
  difficulty: number;
  is_new: boolean;
}

interface ReviewResult {
  grade_label: string;
  interval_days: number;
  message: string;
}

type Phase = 'loading' | 'practising' | 'done' | 'empty' | 'error';

export function PracticeSession({
  token,
  blocks,
}: {
  token: string;
  blocks: ContentBlock[];
}) {
  const { profile } = useProfile();
  const announce = useAnnounce();

  const [phase, setPhase] = useState<Phase>('loading');
  const [items, setItems] = useState<SessionItem[]>([]);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [attempts, setAttempts] = useState(1);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

  // ── build the session ──────────────────────────────────────────────────────

  const start = useCallback(async () => {
    setPhase('loading');
    setError(null);

    const response = await fetch(`${BASE_URL}/practice/session`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        // The learner's own preferred length and modality decide the size of
        // the session, so an AAC user gets fewer items rather than a rushed one.
        session_length_target_min: profile.interaction?.session_length_target_min ?? 5,
        input_mode: profile.input_channels[0] ?? 'text',
        one_step_per_screen: profile.presentation?.one_step_per_screen ?? false,
      }),
    }).catch(() => null);

    if (!response?.ok) {
      setError('We could not load your practice just now. Please try again shortly.');
      setPhase('error');
      return;
    }

    const body = await response.json();
    setItems(body.items);
    setNote(body.note ?? null);
    setIndex(0);
    setAttempts(1);
    setResult(null);
    setPhase(body.items.length ? 'practising' : 'empty');

    if (body.items.length) announce(`${body.items.length} phrases to practise.`);
  }, [announce, profile, token]);

  // Once, on mount. `start` depends on the profile, and the profile object
  // changes identity whenever the provider re-renders — so a plain dependency
  // array would rebuild the session under a learner who is halfway through it.
  // A guard says that out loud instead of suppressing the lint rule.
  const hasStarted = useRef(false);

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;
    void start();
  }, [start]);

  // ── answer one ─────────────────────────────────────────────────────────────

  const item = items[index];
  const block = item ? blocks.find((candidate) => candidate.id === item.block_id) : undefined;

  const submit = useCallback(
    async (response: LearnerResponse) => {
      if (!item) return;

      const correct = normaliseAnswer(response.canonical_text) === normaliseAnswer(item.canonical_text);

      // Below the threshold we do not trust the transcription enough to call it
      // right OR wrong. The server records it as not counting against them.
      const unreliable =
        response.input_mode === 'speech' &&
        typeof response.confidence === 'number' &&
        response.confidence < CONFIDENCE_CONFIRM_THRESHOLD;

      const graded = await fetch(`${BASE_URL}/practice/review`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          block_id: item.block_id,
          correct,
          attempts,
          low_confidence_input: unreliable,
          ...(response.self_report?.confidence
            ? { confidence: response.self_report.confidence }
            : {}),
        }),
      }).catch(() => null);

      if (!graded?.ok) {
        setError('We could not save that answer. Your place is kept — please try again.');
        return;
      }

      const body = (await graded.json()) as ReviewResult;
      setResult(body);
      announce(body.message);
    },
    [announce, attempts, item, token],
  );

  const next = useCallback(() => {
    setResult(null);
    setAttempts(1);

    if (index + 1 >= items.length) {
      setPhase('done');
      announce('Session complete. Well done.');
      return;
    }

    setIndex(index + 1);
  }, [announce, index, items.length]);

  const tryAgain = useCallback(() => {
    setResult(null);
    setAttempts((count) => count + 1);
    announce('Try again');
  }, [announce]);

  // ── states ─────────────────────────────────────────────────────────────────

  if (phase === 'loading') return <p role="status">Getting your practice ready…</p>;

  if (phase === 'error') {
    return (
      <section style={panel}>
        <p data-testid="practice-error" role="alert">
          {error}
        </p>
        <button type="button" onClick={() => void start()} style={primary}>
          Try again
        </button>
      </section>
    );
  }

  if (phase === 'empty') {
    return (
      <section style={panel}>
        <h2 style={{ marginTop: 0 }}>Nothing due right now</h2>
        {/* Framed as an achievement, never as an empty state. Coming back to
            find nothing to do should feel like finishing, not like a dead end. */}
        <p>{note ?? 'You are all caught up. Come back tomorrow for the next few.'}</p>
      </section>
    );
  }

  if (phase === 'done') {
    return (
      <section style={panel}>
        <h2 style={{ marginTop: 0 }}>That is your practice done</h2>
        <p>
          You worked through {items.length} {items.length === 1 ? 'phrase' : 'phrases'}. That is
          worth doing again tomorrow.
        </p>
        <button type="button" onClick={() => void start()} style={primary}>
          Practise some more
        </button>
      </section>
    );
  }

  return (
    <section aria-labelledby="practice-heading">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <h2 id="practice-heading" style={{ margin: 0 }}>
          {item?.is_new ? 'A new phrase' : 'Say this again'}
        </h2>
        {/* Orientation, never a countdown. */}
        <p role="status" style={{ margin: 0, color: 'var(--colour-fg-muted)' }}>
          {index + 1} of {items.length}
        </p>
      </div>

      {block && (
        <div style={{ ...panel, margin: 'var(--space-lg, 1.5rem) 0' }}>
          <ModalityRouter block={block} />
        </div>
      )}

      {error && (
        <p data-testid="practice-error" role="alert" style={panel}>
          {error}
        </p>
      )}

      {result ? (
        <Feedback result={result} onNext={next} onRetry={tryAgain} />
      ) : (
        block && (
          <ModalityInput
            key={`${item?.block_id}-${attempts}`}
            block={block}
            sessionId="practice"
            onResponse={submit}
          />
        )
      )}
    </section>
  );
}

function Feedback({
  result,
  onNext,
  onRetry,
}: {
  result: ReviewResult;
  onNext: () => void;
  onRetry: () => void;
}) {
  // "Again" is FSRS's lowest grade. The learner is never shown that word — they
  // are offered another go, which is the same information without the verdict.
  const offerRetry = result.grade_label === 'Again';

  return (
    <section aria-labelledby="feedback-heading" style={panel}>
      <h3 id="feedback-heading" className="visually-hidden">
        How that went
      </h3>

      <p style={{ margin: '0 0 var(--space-md, 1rem)', fontSize: '1.125rem' }}>{result.message}</p>

      <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
        {offerRetry && (
          <button type="button" onClick={onRetry} style={secondary}>
            Let me try that again
          </button>
        )}
        <button type="button" onClick={onNext} style={primary} autoFocus>
          Next
        </button>
      </div>
    </section>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-lg, 14px)',
  padding: 'var(--space-lg, 1.5rem)',
} as const;

const primary = {
  minHeight: 'var(--target-min, 44px)',
  padding: '0 var(--space-xl, 2.5rem)',
  border: '2px solid var(--colour-border)',
  borderRadius: 8,
  background: 'var(--colour-accent)',
  color: 'var(--colour-accent-fg)',
  fontWeight: 700,
  cursor: 'pointer',
  font: 'inherit',
} as const;

const secondary = {
  ...primary,
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  fontWeight: 400,
} as const;

/**
 * The mock interview — the flagship feature (M11).
 *
 * Every question renders through `<ModalityRouter>` and every answer is given
 * through `<ModalityInput>`, so a Deaf learner sits the same interview as a
 * speaking one, and a non-verbal learner sits it by tapping symbols. That is a
 * first-class path, not a fallback.
 *
 * FOUR THINGS THIS SCREEN WILL NOT DO
 * -----------------------------------
 * 1. **No timer.** Not on a question, not on the interview. Ethics E6. Progress
 *    reads "Question 4 of about 10" — orientation, never a countdown.
 * 2. **Pause always works**, at any question, and says so up front. A learner
 *    with fatigue or anxiety must never feel committed to finishing in one go.
 * 3. **Feedback leads with strengths**, and shows at most two improvement
 *    points. More is not more helpful; it is demoralising and unusable.
 * 4. **It never shows a blank screen on failure.** An outage says what happened
 *    and what still works.
 */
import { useCallback, useRef, useState } from 'react';
import type { ContentBlock, LearnerResponse } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';
import { ModalityInput, ModalityRouter } from '@/modality';
import { api, type InterviewTrack, type Persona, type ScoreResponse } from '@/services/api';

type Phase = 'setup' | 'asking' | 'paused' | 'finished';

const TRACKS: { value: InterviewTrack; label: string; hint: string }[] = [
  { value: 'hr', label: 'General questions', hint: 'About you and how you work' },
  { value: 'role', label: 'About the job', hint: 'Questions about the work itself' },
  { value: 'telephonic', label: 'On the phone', hint: 'No faces — harder, and worth practising' },
];

const PERSONAS: { value: Persona; label: string; hint: string }[] = [
  { value: 'supportive', label: 'Patient', hint: 'Gives you time and encouragement' },
  { value: 'neutral', label: 'Neutral', hint: 'Like most real interviews' },
  { value: 'brisk', label: 'Brisk', hint: 'Moves quickly. Try this once you feel ready.' },
];

export function InterviewSession({ userId = 'demo-learner' }: { userId?: string }) {
  const announce = useAnnounce();

  const [phase, setPhase] = useState<Phase>('setup');
  const [track, setTrack] = useState<InterviewTrack>('hr');
  const [persona, setPersona] = useState<Persona>('supportive');
  const [jobContext, setJobContext] = useState('');

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState<ContentBlock | null>(null);
  const [progress, setProgress] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<ScoreResponse | null>(null);

  const askedRef = useRef<string>('');

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);

    const result = await api.startInterview(userId, track, persona, jobContext);
    setBusy(false);

    if (!result.ok) {
      setError(result.message);
      return;
    }

    askedRef.current = result.data.block.canonical_text;
    setConversationId(result.data.conversation_id);
    setQuestion(result.data.block);
    setProgress(result.data.progress);
    setPhase('asking');
    announce('Interview started. You can pause at any time.');
  }, [announce, jobContext, persona, track, userId]);

  const submit = useCallback(
    async (response: LearnerResponse) => {
      if (!conversationId) return;

      setBusy(true);
      setError(null);
      const answered = askedRef.current;

      const next = await api.answer(conversationId, userId, response.canonical_text);

      if (!next.ok) {
        setBusy(false);
        // The answer is not lost — the gateway leaves state untouched on
        // failure, so retrying replays the same question.
        setError(next.message);
        return;
      }

      // Scored separately, and never allowed to block progress: a scoring
      // outage must not end someone's interview.
      const scored = await api.score(userId, answered, response.canonical_text);
      setFeedback(scored.ok ? scored.data : null);

      askedRef.current = next.data.block.canonical_text;
      setQuestion(next.data.block);
      setProgress(next.data.progress);
      setBusy(false);

      if (next.data.finished) {
        setPhase('finished');
        announce('Interview complete. Well done.');
      } else {
        announce('Next question');
      }
    },
    [announce, conversationId, userId],
  );

  const pause = useCallback(async () => {
    if (!conversationId) return;
    const result = await api.pauseInterview(conversationId, userId);
    setPhase('paused');
    announce(result.ok ? result.data.message : 'Paused. Your place is saved.');
  }, [announce, conversationId, userId]);

  // ── setup ──────────────────────────────────────────────────────────────────

  if (phase === 'setup') {
    return (
      <section aria-labelledby="setup-heading" style={panel}>
        <h2 id="setup-heading" style={{ marginTop: 0 }}>
          Practise an interview
        </h2>
        <p style={{ color: 'var(--colour-fg-muted)', maxWidth: '60ch' }}>
          Nobody is watching and nothing is timed. You can stop at any question and come back
          later — your place is saved.
        </p>

        <ChoiceGroup
          legend="What kind of interview?"
          name="track"
          options={TRACKS}
          selected={track}
          onSelect={setTrack}
        />
        <ChoiceGroup
          legend="How should the interviewer be?"
          name="persona"
          options={PERSONAS}
          selected={persona}
          onSelect={setPersona}
        />

        <p>
          <label htmlFor="job" style={{ display: 'block', fontWeight: 700, marginBottom: '.5rem' }}>
            What job is this for? <span style={{ fontWeight: 400 }}>(optional)</span>
          </label>
          <input
            id="job"
            value={jobContext}
            onChange={(event) => setJobContext(event.target.value)}
            placeholder="packaging unit operator"
            style={field}
          />
        </p>

        {error && <ErrorNote message={error} />}

        <button type="button" onClick={start} disabled={busy} style={primary(busy)}>
          {busy ? 'Getting ready…' : 'Start the interview'}
        </button>
      </section>
    );
  }

  // ── paused ─────────────────────────────────────────────────────────────────

  if (phase === 'paused') {
    return (
      <section aria-labelledby="paused-heading" style={panel}>
        <h2 id="paused-heading" style={{ marginTop: 0 }}>
          Paused
        </h2>
        <p>Your place is saved. Come back whenever you are ready.</p>
        <button type="button" onClick={() => setPhase('asking')} style={primary(false)}>
          Carry on
        </button>
      </section>
    );
  }

  // ── finished ───────────────────────────────────────────────────────────────

  if (phase === 'finished') {
    return (
      <section aria-labelledby="done-heading" style={panel}>
        <h2 id="done-heading" style={{ marginTop: 0 }}>
          That is the whole interview
        </h2>
        <p>You answered every question. That is worth doing again whenever you like.</p>
        {feedback && <Feedback feedback={feedback} />}
      </section>
    );
  }

  // ── asking ─────────────────────────────────────────────────────────────────

  return (
    <section aria-labelledby="question-heading" style={panel}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <h2 id="question-heading" style={{ margin: 0 }}>
          The interviewer asks
        </h2>
        {/* Orientation, not a countdown. Ethics E6. */}
        <p role="status" style={{ margin: 0, color: 'var(--colour-fg-muted)' }}>
          {progress}
        </p>
      </div>

      {question && (
        <div style={{ margin: 'var(--space-lg, 1.5rem) 0' }}>
          <ModalityRouter block={question} />
        </div>
      )}

      {error && <ErrorNote message={error} />}

      {question && conversationId && (
        <ModalityInput
          key={question.id}
          block={question}
          sessionId={conversationId}
          onResponse={submit}
          disabled={busy}
        />
      )}

      {feedback && <Feedback feedback={feedback} />}

      <p style={{ marginTop: 'var(--space-lg, 1.5rem)' }}>
        <button type="button" onClick={pause} style={secondary}>
          Pause — save my place
        </button>
      </p>
    </section>
  );
}

// ── pieces ───────────────────────────────────────────────────────────────────

function Feedback({ feedback }: { feedback: ScoreResponse }) {
  if (!feedback.scored) {
    return feedback.unavailable_message ? <ErrorNote message={feedback.unavailable_message} /> : null;
  }

  return (
    <section
      aria-labelledby="feedback-heading"
      style={{ ...panel, background: 'var(--colour-bg)', marginTop: 'var(--space-lg, 1.5rem)' }}
    >
      <h3 id="feedback-heading" style={{ marginTop: 0 }}>
        About that answer
      </h3>

      {/* Strengths first, always. Ethics Charter copy rules. */}
      {feedback.strengths.length > 0 && (
        <>
          <h4 style={{ marginBottom: '.25rem' }}>What worked</h4>
          <ul>
            {feedback.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}

      {feedback.improvements.length > 0 && (
        <>
          <h4 style={{ marginBottom: '.25rem' }}>One thing to try next time</h4>
          {/* At most two. More is demoralising and unusable. */}
          <ul>
            {feedback.improvements.slice(0, 2).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}

      <p style={{ color: 'var(--colour-fg-muted)', fontSize: '.95rem', marginBottom: 0 }}>
        This looks at what you said, not how you said it.
      </p>
    </section>
  );
}

function ChoiceGroup<T extends string>({
  legend,
  name,
  options,
  selected,
  onSelect,
}: {
  legend: string;
  name: string;
  options: { value: T; label: string; hint: string }[];
  selected: T;
  onSelect: (value: T) => void;
}) {
  return (
    <fieldset style={{ border: '1px solid var(--colour-border)', borderRadius: 8, margin: '1rem 0' }}>
      <legend style={{ padding: '0 .5rem', fontWeight: 700 }}>{legend}</legend>
      {options.map((option) => (
        <label
          key={option.value}
          style={{
            display: 'flex',
            gap: '.75rem',
            alignItems: 'flex-start',
            minHeight: 'var(--target-min, 44px)',
            padding: '.5rem',
            cursor: 'pointer',
          }}
        >
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={selected === option.value}
            onChange={() => onSelect(option.value)}
            style={{ marginTop: '.35rem' }}
          />
          <span>
            <strong>{option.label}</strong>
            <br />
            <span style={{ color: 'var(--colour-fg-muted)' }}>{option.hint}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

function ErrorNote({ message }: { message: string }) {
  return (
    <p
      // role="alert" is correct here AND on the global Announcer's assertive
      // region, so the two are indistinguishable by role alone. The test id is
      // how a test targets this one specifically.
      data-testid="error-note"
      role="alert"
      style={{
        padding: 'var(--space-md, 1rem)',
        border: '1px solid var(--colour-border)',
        borderRadius: 8,
        background: 'var(--colour-surface)',
      }}
    >
      {message}
    </p>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-lg, 14px)',
  padding: 'var(--space-lg, 1.5rem)',
} as const;

const field = {
  width: '100%',
  maxWidth: '30rem',
  font: 'inherit',
  minHeight: 'var(--target-min, 44px)',
  padding: '.5rem',
  color: 'var(--colour-fg)',
  background: 'var(--colour-bg)',
  border: '1px solid var(--colour-border)',
  borderRadius: 8,
} as const;

const secondary = {
  minHeight: 'var(--target-min, 44px)',
  padding: '0 1rem',
  border: '1px solid var(--colour-border)',
  borderRadius: 8,
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  cursor: 'pointer',
  font: 'inherit',
} as const;

const primary = (disabled: boolean) =>
  ({
    minHeight: 'var(--target-min, 44px)',
    padding: '0 1.5rem',
    border: '1px solid var(--colour-border)',
    borderRadius: 8,
    background: disabled ? 'var(--colour-surface)' : 'var(--colour-accent)',
    color: disabled ? 'var(--colour-fg-muted)' : 'var(--colour-accent-fg)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 700,
    font: 'inherit',
  }) as const;

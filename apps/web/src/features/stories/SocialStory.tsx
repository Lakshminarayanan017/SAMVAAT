/**
 * Social stories (M10) — the reading surface.
 *
 * The endpoint has worked since M10 and nothing in the product could open one.
 * That is the "built, not done" state docs/STATUS.md exists to make visible,
 * and this file closes the last instance of it.
 *
 * FOUR THINGS THIS SCREEN MUST GET RIGHT
 * --------------------------------------
 * 1. **One panel at a time.** A social story is read to understand a situation,
 *    not skimmed. Showing eight panels at once defeats the entire structure and
 *    is unusable for someone who reads Easy-Read.
 *
 * 2. **The learner moves.** No auto-advance, no timer, no countdown anywhere
 *    (Ethics E6). A learner who needs four minutes on one panel takes four
 *    minutes, and nothing on screen suggests that is slow.
 *
 * 3. **The AI label is not dismissable.** If a model wrote this, the learner is
 *    told so on every panel — not once in a banner they scrolled past. A draft
 *    awaiting a trainer says that too. Both are honest; neither pretends a
 *    person wrote something a model did (Ethics E5).
 *
 * 4. **Panels go through the Modality Router.** Generated prose gets exactly the
 *    same accessibility treatment as the authored phrase bank. See toBlock.ts —
 *    that is the whole reason the conversion exists.
 */
import { useCallback, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';
import { ModalityRouter } from '@/modality';
import { panelToBlock, type Story } from '@/features/stories/toBlock';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface SocialStoryProps {
  token: string;
  /** Where the learner works or hopes to, e.g. "a supermarket stockroom". */
  jobContext: string;
  /** The situation that is confusing, e.g. "my supervisor asks me to redo a task". */
  situation: string;
  readingLevel?: 'standard' | 'easy_read';
}

export function SocialStory({
  token,
  jobContext,
  situation,
  readingLevel = 'easy_read',
}: SocialStoryProps) {
  const announce = useAnnounce();
  const [story, setStory] = useState<Story | null>(null);
  const [panelIndex, setPanelIndex] = useState(0);
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');

  const load = useCallback(async () => {
    setState('loading');
    announce('Making your story. This can take a few moments.');

    const response = await fetch(`${BASE_URL}/stories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        job_context: jobContext,
        situation,
        reading_level: readingLevel,
        has_trainer: false,
      }),
    }).catch(() => null);

    if (!response?.ok) {
      setState('error');
      return;
    }

    const body = (await response.json()) as Story;
    setStory(body);
    setPanelIndex(0);
    setState('idle');
    announce(`Your story is ready. ${body.title}. ${body.panels.length} pages.`);
  }, [announce, jobContext, readingLevel, situation, token]);

  const move = useCallback(
    (delta: number) => {
      if (!story) return;
      const next = Math.min(Math.max(panelIndex + delta, 0), story.panels.length - 1);
      setPanelIndex(next);
      announce(`Page ${next + 1} of ${story.panels.length}.`);
    },
    [announce, panelIndex, story],
  );

  if (state === 'error') {
    return (
      <section style={panel}>
        <p data-testid="story-error" role="alert">
          We could not make your story just now. Nothing is lost — you can try again.
        </p>
        <button type="button" onClick={() => void load()} style={button}>
          Try again
        </button>
      </section>
    );
  }

  if (!story) {
    return (
      <section aria-labelledby="story-intro">
        <h2 id="story-intro" style={{ marginTop: 0 }}>
          A story about {situation}
        </h2>
        <p style={{ maxWidth: '58ch' }}>
          A story explains what usually happens, and what you can do. You read it at your own
          speed. There is no test at the end.
        </p>
        <button
          type="button"
          onClick={() => void load()}
          disabled={state === 'loading'}
          style={button}
        >
          {state === 'loading' ? 'Making your story…' : 'Make my story'}
        </button>
      </section>
    );
  }

  const current = story.panels[panelIndex];
  if (!current) return null;

  const block = panelToBlock(current, panelIndex, 'story.generated');
  const isFirst = panelIndex === 0;
  const isLast = panelIndex === story.panels.length - 1;

  return (
    <section aria-labelledby="story-title">
      <h2 id="story-title" style={{ marginTop: 0 }}>
        {story.title}
      </h2>

      <Provenance story={story} />

      {/* aria-live is deliberately absent: the panel change is announced once,
          by hand, in `move`. A live region here would say it twice. */}
      <article
        aria-label={`Page ${panelIndex + 1} of ${story.panels.length}`}
        style={{ ...panel, margin: 'var(--space-lg, 1.5rem) 0', minHeight: '9rem' }}
      >
        <ModalityRouter block={block} />
      </article>

      <nav aria-label="Story pages" style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
        <button type="button" onClick={() => move(-1)} disabled={isFirst} style={button}>
          Back
        </button>
        <button type="button" onClick={() => move(1)} disabled={isLast} style={button}>
          {isLast ? 'This is the end' : 'Next'}
        </button>
      </nav>

      <p style={{ marginTop: '.75rem', color: 'var(--colour-fg-muted)' }}>
        Page {panelIndex + 1} of {story.panels.length}. You can read this as many times as you
        like.
      </p>
    </section>
  );
}

/**
 * Who wrote this, and has anyone checked it.
 *
 * Rendered above the panel and on every page, because a label the learner saw
 * once on page one is not a label they are reading now. Not dismissable, for
 * the same reason.
 */
function Provenance({ story }: { story: Story }) {
  if (!story.generated && story.status === 'published') return null;

  return (
    <p
      data-testid="story-provenance"
      style={{
        ...panel,
        borderLeft: '4px solid var(--colour-border)',
        margin: 0,
      }}
    >
      {story.generated && (
        <span>
          <strong>Written by a computer.</strong> It is meant to help, and it can be wrong.{' '}
        </span>
      )}
      {story.status === 'draft' && (
        <span>Your trainer has not read this yet. It may change.</span>
      )}
      {story.notice && <span> {story.notice}</span>}
    </p>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  padding: 'var(--space-md, 1rem)',
} as const;

const button = {
  minHeight: '3rem',
  minWidth: '7rem',
  padding: '.75rem 1.25rem',
  fontSize: '1.05rem',
  borderRadius: 'var(--radius-md, 8px)',
  border: '1px solid var(--colour-border)',
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  cursor: 'pointer',
} as const;

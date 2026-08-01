/**
 * Choosing which situation to get a story about.
 *
 * WHY A LIST AND NOT A TEXT BOX
 * -----------------------------
 * A free-text field would be the obvious design and the wrong one, twice over.
 *
 * Accessibility: describing a confusing situation in writing is precisely the
 * skill a learner comes here lacking. P4 (intellectual disability) and P2
 * (non-verbal, switch access) would both be shut out of the feature by its own
 * front door.
 *
 * Safety: free text goes to a language model. A fixed list means the only
 * learner-controlled part of the prompt is an index into an array we wrote.
 *
 * The situations below are the ones support workers report most often from
 * supported-employment placements in India. They are ordinary workplace
 * confusions, not deficits — none of them frames the learner as the problem.
 */
import { useState } from 'react';

import { SocialStory } from '@/features/stories/SocialStory';

interface Situation {
  id: string;
  /** What the learner reads on the button. First person, plain. */
  label: string;
  /** What the generator is told. Fuller, still first person. */
  situation: string;
  jobContext: string;
}

const SITUATIONS: Situation[] = [
  {
    id: 'redo',
    label: 'My supervisor asks me to do something again',
    situation: 'my supervisor asks me to do a task again',
    jobContext: 'my workplace',
  },
  {
    id: 'break',
    label: 'I need to ask for a break',
    situation: 'I need a break but everyone else is still working',
    jobContext: 'my workplace',
  },
  {
    id: 'notunderstood',
    label: 'I did not understand what someone said',
    situation: 'someone gives me an instruction and I do not understand it',
    jobContext: 'my workplace',
  },
  {
    id: 'firstday',
    label: 'It is my first day',
    situation: 'it is my first day at a new job and I do not know anyone',
    jobContext: 'a new workplace',
  },
  {
    id: 'mistake',
    label: 'I made a mistake at work',
    situation: 'I made a mistake at work and I need to tell someone',
    jobContext: 'my workplace',
  },
  {
    id: 'lunch',
    label: 'People are talking and I do not know how to join in',
    situation: 'my colleagues are chatting at lunch and I want to join in',
    jobContext: 'my workplace',
  },
];

export function StoryChooser({ token }: { token: string }) {
  const [chosen, setChosen] = useState<Situation | null>(null);

  if (chosen) {
    return (
      <div>
        <button type="button" onClick={() => setChosen(null)} style={{ ...button, marginBottom: '1rem' }}>
          Choose a different situation
        </button>
        {/* Keyed so choosing another situation resets the story rather than
            leaving the previous one's panels on screen. */}
        <SocialStory
          key={chosen.id}
          token={token}
          jobContext={chosen.jobContext}
          situation={chosen.situation}
        />
      </div>
    );
  }

  return (
    <section aria-labelledby="chooser-heading">
      <h2 id="chooser-heading" style={{ marginTop: 0 }}>
        What would you like to understand?
      </h2>
      <p style={{ maxWidth: '58ch' }}>
        Pick something that has happened, or something you are worried about. You will get a short
        story that explains it.
      </p>

      <ul
        style={{
          listStyle: 'none',
          padding: 0,
          margin: 0,
          display: 'grid',
          gap: '.75rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(18rem, 1fr))',
        }}
      >
        {SITUATIONS.map((situation) => (
          <li key={situation.id}>
            <button
              type="button"
              onClick={() => setChosen(situation)}
              style={{ ...button, width: '100%', textAlign: 'left', minHeight: '4rem' }}
            >
              {situation.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

const button = {
  padding: '.9rem 1.25rem',
  fontSize: '1.05rem',
  borderRadius: 'var(--radius-md, 8px)',
  border: '1px solid var(--colour-border)',
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  cursor: 'pointer',
} as const;

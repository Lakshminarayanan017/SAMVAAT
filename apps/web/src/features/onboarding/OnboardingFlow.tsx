/**
 * Onboarding (M1).
 *
 * Three stages, each requiring more of the learner than the last:
 *
 *   0. Detect      what the browser already tells us — reduced motion, contrast
 *                  preference, colour scheme. Costs the learner nothing.
 *   1. Four doors  the one screen that must work for everyone at once.
 *   2. Confirm     the remaining questions, asked THROUGH the channel they just
 *                  chose. By now we can speak their language, so this stage is
 *                  allowed to be ordinary.
 *
 * Speech enrolment (stage 3, feeding M8) is deliberately not here. It is thirty
 * phrases, and putting it between a learner and their first lesson would lose
 * the people who most need the app. It is offered later, skippable and
 * resumable, once they have seen the point of it.
 *
 * WHAT THIS SCREEN WILL NOT DO
 * ----------------------------
 * It never asks for a diagnosis. It asks what someone can *use* — which is the
 * only thing the router needs, and the only thing anyone owes us.
 */
import { useCallback, useEffect, useState } from 'react';
import type { CommunicationAbilityProfile, InputMode, OutputChannel } from '@samvaad/contracts';

import { useAnnounce } from '@/a11y/Announcer';

import { FourDoorScreen, type Door } from './FourDoorScreen';

/** Stage 0 — what the browser already knows. */
export function detectPreferences(): Partial<
  NonNullable<CommunicationAbilityProfile['presentation']>
> {
  if (typeof window === 'undefined' || !window.matchMedia) return {};

  const asks = (query: string) => window.matchMedia(query).matches;

  return {
    motion_reduced: asks('(prefers-reduced-motion: reduce)'),
    contrast_theme: asks('(prefers-contrast: more)') ? 'high_contrast' : 'standard',
    colour_scheme: asks('(prefers-color-scheme: dark)') ? 'dark' : 'light',
    // A coarse pointer means touch or a switch-driven cursor. Bigger targets
    // help both and cost a mouse user nothing.
    target_size_px: asks('(pointer: coarse)') ? 56 : 44,
  };
}

/** Stage 1 — what each door means for the profile. */
const DOOR_PROFILE: Record<
  Door,
  { output: OutputChannel[]; input: InputMode[]; easyRead: boolean }
> = {
  listen: {
    output: ['audio', 'captioned_text'],
    input: ['speech', 'text'],
    easyRead: false,
  },
  read: {
    output: ['captioned_text', 'audio'],
    input: ['text', 'speech'],
    easyRead: false,
  },
  sign: {
    // Captions alongside, always: our ISL library covers 100 phrases, and a
    // Deaf learner meeting an unsigned one must not hit a blank screen.
    output: ['isl', 'captioned_text'],
    input: ['text', 'sign'],
    easyRead: false,
  },
  pictures: {
    output: ['easy_read', 'pictograph', 'audio'],
    input: ['aac', 'text'],
    easyRead: true,
  },
};

type Stage = 'doors' | 'confirm';

interface Question {
  id: 'speaks' | 'bigger' | 'slower' | 'switch';
  prompt: string;
  hint: string;
  /** Only asked when it could change the profile. */
  when: (door: Door) => boolean;
}

const QUESTIONS: Question[] = [
  {
    id: 'speaks',
    prompt: 'Will you answer by speaking?',
    hint: 'You can always type or tap instead.',
    when: (door) => door !== 'pictures',
  },
  {
    id: 'bigger',
    prompt: 'Would bigger buttons help?',
    hint: 'Useful if tapping small things is hard.',
    when: () => true,
  },
  {
    id: 'slower',
    prompt: 'Would slower speech help?',
    hint: 'We will play recordings more slowly.',
    when: (door) => door === 'listen' || door === 'pictures',
  },
  {
    id: 'switch',
    prompt: 'Do you use a switch or a button device?',
    hint: 'We will highlight one choice at a time for you.',
    when: () => true,
  },
];

export function OnboardingFlow({
  onComplete,
  saving = false,
  error = null,
}: {
  onComplete: (profile: Partial<CommunicationAbilityProfile>) => void;
  saving?: boolean;
  error?: string | null;
}) {
  const announce = useAnnounce();
  const [stage, setStage] = useState<Stage>('doors');
  const [door, setDoor] = useState<Door | null>(null);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (stage === 'confirm') announce('A few more questions.');
  }, [stage, announce]);

  const choose = useCallback((chosen: Door) => {
    setDoor(chosen);
    setStage('confirm');
  }, []);

  const finish = useCallback(() => {
    if (!door) return;

    const base = DOOR_PROFILE[door];
    const detected = detectPreferences();

    const input: InputMode[] = [...base.input];
    // Only removed if they said no. Silence is not a "no" — assuming it would
    // strip a channel nobody asked us to remove.
    if (answers['speaks'] === false) {
      const index = input.indexOf('speech');
      if (index >= 0) input.splice(index, 1);
    }
    if (answers['switch']) input.push('switch');

    onComplete({
      input_channels: input.length ? input : ['text'],
      output_channels: base.output,
      text_complexity: base.easyRead ? 'easy_read' : 'standard',
      speech_status: answers['speaks'] === false ? 'nonverbal' : 'undeclared',
      primary_language: 'en-IN',
      presentation: {
        ...detected,
        audio_rate: answers['slower'] ? 0.8 : 1.0,
        target_size_px: answers['bigger'] ? 88 : (detected.target_size_px ?? 44),
        captions_enabled: true,
        one_step_per_screen: base.easyRead,
      },
      interaction: answers['switch']
        ? {
            switch_scanning: {
              enabled: true,
              switch_count: 2,
              dwell_ms: 1200,
              scan_mode: 'row_column',
            },
          }
        : undefined,
    } as Partial<CommunicationAbilityProfile>);
  }, [answers, door, onComplete]);

  if (stage === 'doors') return <FourDoorScreen onChoose={choose} />;

  const asked = QUESTIONS.filter((question) => question.when(door!));

  return (
    <section aria-labelledby="confirm-heading" style={{ maxWidth: '44rem', margin: '0 auto' }}>
      <h1 id="confirm-heading" style={{ marginTop: 0 }}>
        A few more questions
      </h1>
      <p style={{ color: 'var(--colour-fg-muted)' }}>
        Only four, and you can change any of them later. There are no wrong answers.
      </p>

      {asked.map((question) => (
        <fieldset
          key={question.id}
          style={{
            border: '2px solid var(--colour-border)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: 'var(--space-md, 1rem)',
            margin: 'var(--space-md, 1rem) 0',
          }}
        >
          <legend style={{ padding: '0 .5rem', fontWeight: 700, fontSize: '1.125rem' }}>
            {question.prompt}
          </legend>
          <p style={{ margin: '0 0 .75rem', color: 'var(--colour-fg-muted)' }}>{question.hint}</p>

          <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
            {[
              { value: true, label: 'Yes' },
              { value: false, label: 'No' },
            ].map((option) => (
              <label
                key={String(option.value)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '.5rem',
                  minHeight: 'var(--target-min, 44px)',
                  padding: '0 var(--space-md, 1rem)',
                  border: '2px solid var(--colour-border)',
                  borderRadius: 'var(--radius-md, 8px)',
                  cursor: 'pointer',
                  background:
                    answers[question.id] === option.value
                      ? 'var(--colour-accent)'
                      : 'var(--colour-surface)',
                  color:
                    answers[question.id] === option.value
                      ? 'var(--colour-accent-fg)'
                      : 'var(--colour-fg)',
                }}
              >
                <input
                  type="radio"
                  name={question.id}
                  checked={answers[question.id] === option.value}
                  onChange={() =>
                    setAnswers((current) => ({ ...current, [question.id]: option.value }))
                  }
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      ))}

      {error && (
        <p data-testid="onboarding-error" role="alert" style={{ fontWeight: 700 }}>
          {error}
        </p>
      )}

      <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
        <button
          type="button"
          onClick={finish}
          disabled={saving}
          style={{
            minHeight: 'calc(var(--target-min, 44px) * 1.2)',
            padding: '0 var(--space-xl, 2.5rem)',
            fontSize: '1.125rem',
            fontWeight: 700,
            border: '2px solid var(--colour-border)',
            borderRadius: 'var(--radius-md, 8px)',
            background: saving ? 'var(--colour-surface)' : 'var(--colour-accent)',
            color: saving ? 'var(--colour-fg-muted)' : 'var(--colour-accent-fg)',
            cursor: saving ? 'not-allowed' : 'pointer',
            font: 'inherit',
          }}
        >
          {saving ? 'Saving…' : 'Start using the app'}
        </button>

        {/* Going back must always be possible. A learner who picked the wrong
            door should not be stuck with it for the sake of a tidy flow. */}
        <button
          type="button"
          onClick={() => setStage('doors')}
          disabled={saving}
          style={{
            minHeight: 'calc(var(--target-min, 44px) * 1.2)',
            padding: '0 var(--space-lg, 1.5rem)',
            border: '2px solid var(--colour-border)',
            borderRadius: 'var(--radius-md, 8px)',
            background: 'var(--colour-surface)',
            color: 'var(--colour-fg)',
            cursor: 'pointer',
            font: 'inherit',
          }}
        >
          Go back
        </button>
      </div>
    </section>
  );
}

export { DOOR_PROFILE, QUESTIONS };

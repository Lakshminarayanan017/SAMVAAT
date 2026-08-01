/**
 * My progress (M12, M13, and the learner half of M14).
 *
 * Everything on this screen is the learner measured against themselves. There
 * is no percentile, no cohort average, no "ahead of" or "behind" anything —
 * ADR-0003 applied to motivation as strictly as to scoring.
 *
 * THREE THINGS THIS SCREEN WILL NOT DO
 * ------------------------------------
 * 1. **Never show a streak as being at risk.** The headline number is days
 *    practised, which only goes up. A run is celebrated when it exists and
 *    silently absent when it does not; nothing announces its loss.
 *
 * 2. **Never present a locked badge as a failure.** Unearned badges are shown
 *    as a map of what exists, greyed but legible, with the same text. Hidden
 *    goals are a dark pattern; visible ones are direction.
 *
 * 3. **Never give a recommendation without a reason.** Every suggestion carries
 *    the sentence the API generated, verbatim. A learner who cannot interrogate
 *    a suggestion has to take it on trust, and trust is what a disabled learner
 *    has least reason to extend to an algorithm.
 */
import { useCallback, useEffect, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface Badge {
  id: string;
  family: string;
  label: string;
  earned_message: string;
}

export interface Progress {
  xp: number;
  days_practised: number;
  current_run: number;
  longest_run: number;
  summary: string;
  phrases_started: number;
  phrases_reliable: number;
  interviews_completed: number;
  badges: Badge[];
}

export interface Suggestion {
  block_id: string;
  canonical_text: string;
  explanation: string;
  reason: string;
}

const FAMILY_LABEL: Record<string, string> = {
  consistency: 'Coming back',
  mastery: 'Phrases you know',
  courage: 'Hard conversations',
  growth: 'Your own progress',
};

export function ProgressPanel({ token }: { token: string }) {
  const announce = useAnnounce();
  const [progress, setProgress] = useState<Progress | null>(null);
  const [allBadges, setAllBadges] = useState<Badge[]>([]);
  const [next, setNext] = useState<Suggestion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const headers = { Authorization: `Bearer ${token}` };

    const [progressResponse, badgesResponse, nextResponse] = await Promise.all([
      fetch(`${BASE_URL}/progress`, { headers }).catch(() => null),
      fetch(`${BASE_URL}/progress/badges`, { headers }).catch(() => null),
      fetch(`${BASE_URL}/progress/next?limit=4`, { headers }).catch(() => null),
    ]);

    if (!progressResponse?.ok) {
      setError('We could not load your progress just now. Please try again shortly.');
      return;
    }

    const body = (await progressResponse.json()) as Progress;
    setProgress(body);
    if (badgesResponse?.ok) setAllBadges(await badgesResponse.json());
    if (nextResponse?.ok) setNext(await nextResponse.json());

    announce(body.summary);
  }, [announce, token]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <p data-testid="progress-error" role="alert" style={panel}>
        {error}
      </p>
    );
  }

  if (!progress) return <p role="status">Loading your progress…</p>;

  const earned = new Set(progress.badges.map((badge) => badge.id));

  return (
    <section aria-labelledby="progress-heading">
      <h2 id="progress-heading" style={{ marginTop: 0 }}>
        How you are doing
      </h2>

      {/* The headline is a number that only ever goes up. */}
      <p style={{ fontSize: '1.375rem', margin: '0 0 var(--space-lg, 1.5rem)' }}>
        {progress.summary}
      </p>

      <ul
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(11rem, 1fr))',
          gap: 'var(--space-md, 1rem)',
          listStyle: 'none',
          padding: 0,
          margin: 0,
        }}
      >
        <Stat label="Effort points" value={progress.xp} hint="Earned for trying, not for being right" />
        <Stat label="Phrases started" value={progress.phrases_started} />
        <Stat
          label="Phrases you can rely on"
          value={progress.phrases_reliable}
          hint="Ones you have remembered over time"
        />
        <Stat label="Interviews practised" value={progress.interviews_completed} />
      </ul>

      {next.length > 0 && <WhatNext suggestions={next} />}

      <Badges all={allBadges} earned={earned} />
    </section>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <li style={panel}>
      {/* Number first visually, but the label is read first by a screen reader
          because it comes first in the accessibility tree via aria-label. */}
      <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700 }} aria-hidden="true">
        {value}
      </p>
      <p style={{ margin: '.25rem 0 0' }}>
        <span className="visually-hidden">{`${label}: ${value}. `}</span>
        <span aria-hidden="true">{label}</span>
      </p>
      {hint && (
        <p style={{ margin: '.25rem 0 0', fontSize: '.9rem', color: 'var(--colour-fg-muted)' }}>
          {hint}
        </p>
      )}
    </li>
  );
}

function WhatNext({ suggestions }: { suggestions: Suggestion[] }) {
  return (
    <section aria-labelledby="next-heading" style={{ marginTop: 'var(--space-xl, 2.5rem)' }}>
      <h3 id="next-heading">What to try next</h3>
      <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '.75rem' }}>
        {suggestions.map((suggestion) => (
          <li key={suggestion.block_id} style={panel}>
            <p style={{ margin: 0, fontWeight: 700 }}>{suggestion.canonical_text}</p>
            {/* The reason, verbatim from the API. The client never re-derives
                it, so there is one wording and it is testable. */}
            <p style={{ margin: '.25rem 0 0', color: 'var(--colour-fg-muted)' }}>
              {suggestion.explanation}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Badges({ all, earned }: { all: Badge[]; earned: Set<string> }) {
  if (all.length === 0) return null;

  const families = [...new Set(all.map((badge) => badge.family))];

  return (
    <section aria-labelledby="badges-heading" style={{ marginTop: 'var(--space-xl, 2.5rem)' }}>
      <h3 id="badges-heading">Badges</h3>
      <p style={{ color: 'var(--colour-fg-muted)' }}>
        Everything there is to earn. Nothing here expires.
      </p>

      {families.map((family) => (
        <section key={family} aria-labelledby={`family-${family}`}>
          <h4 id={`family-${family}`} style={{ marginBottom: '.5rem' }}>
            {FAMILY_LABEL[family] ?? family}
          </h4>
          <ul
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(15rem, 1fr))',
              gap: '.75rem',
              listStyle: 'none',
              padding: 0,
              marginBottom: 'var(--space-lg, 1.5rem)',
            }}
          >
            {all
              .filter((badge) => badge.family === family)
              .map((badge) => {
                const has = earned.has(badge.id);
                return (
                  <li
                    key={badge.id}
                    data-earned={has}
                    style={{
                      ...panel,
                      // Not hidden and not struck through. An unearned badge is
                      // a direction, not a failure.
                      opacity: has ? 1 : 0.72,
                      borderStyle: has ? 'solid' : 'dashed',
                    }}
                  >
                    <p style={{ margin: 0, fontWeight: 700 }}>
                      {badge.label}
                      <span className="visually-hidden">
                        {has ? ' — earned' : ' — not earned yet'}
                      </span>
                    </p>
                    <p style={{ margin: '.25rem 0 0', color: 'var(--colour-fg-muted)' }}>
                      {badge.earned_message}
                    </p>
                  </li>
                );
              })}
          </ul>
        </section>
      ))}
    </section>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  padding: 'var(--space-md, 1rem)',
} as const;

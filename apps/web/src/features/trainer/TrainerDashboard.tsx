/**
 * The trainer dashboard (M14).
 *
 * What turns this from a consumer app into something an institution will
 * deploy — and the screen that makes Ethics E5 visible rather than merely true
 * in the database.
 *
 * TWO THINGS THIS SCREEN IS CAREFUL ABOUT
 * ---------------------------------------
 * **A learner who has not shared is shown, not hidden.** They are on this
 * trainer's caseload, so the trainer needs to know they exist. But every metric
 * is blank and the row says why. Hiding them would be dishonest; showing an
 * error would read as a fault when it is the learner's choice.
 *
 * **Nothing here is a ranking.** No leaderboard, no cohort average with
 * individuals plotted against it, no "bottom performers". A trainer needs to
 * see who might need attention today; a league table of disabled learners is a
 * different thing entirely, and we are not building it.
 *
 * ACCESSIBILITY
 * -------------
 * The cohort is a real `<table>` with proper headers, not a grid of divs — so a
 * screen-reader user can navigate by column and hear "Ravi, cards due, 4"
 * instead of a stream of unlabelled numbers. Trainers are disabled people too.
 */
import { useCallback, useEffect, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface CohortMember {
  learner_user_id: string;
  display_name: string;
  shared: boolean;
  cards_started: number | null;
  cards_due: number | null;
  lapses: number | null;
  interviews_completed: number | null;
  last_active_at: string | null;
  is_active: boolean;
}

interface Agreement {
  scores: number;
  overridden: number;
  agreement: number;
  target_agreement: number;
  note: string;
}

export function TrainerDashboard({ token }: { token: string }) {
  const announce = useAnnounce();
  const [cohort, setCohort] = useState<CohortMember[] | null>(null);
  const [agreement, setAgreement] = useState<Agreement | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const headers = { Authorization: `Bearer ${token}` };

    const [cohortResponse, agreementResponse] = await Promise.all([
      fetch(`${BASE_URL}/trainer/cohort`, { headers }).catch(() => null),
      fetch(`${BASE_URL}/trainer/agreement`, { headers }).catch(() => null),
    ]);

    if (!cohortResponse?.ok) {
      setError('We could not load your caseload just now. Please try again shortly.');
      return;
    }

    const members = (await cohortResponse.json()) as CohortMember[];
    setCohort(members);
    if (agreementResponse?.ok) setAgreement(await agreementResponse.json());

    announce(`${members.length} learners on your caseload.`);
  }, [announce, token]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <p data-testid="trainer-error" role="alert" style={panel}>
        {error}
      </p>
    );
  }

  if (cohort === null) {
    return <p role="status">Loading your caseload…</p>;
  }

  const sharing = cohort.filter((member) => member.shared);
  const waiting = cohort.length - sharing.length;

  return (
    <section aria-labelledby="cohort-heading">
      <h2 id="cohort-heading" style={{ marginTop: 0 }}>
        Your learners
      </h2>

      <p style={{ color: 'var(--colour-fg-muted)' }}>
        {cohort.length} on your caseload
        {waiting > 0 && `, ${waiting} not sharing their progress yet`}.
      </p>

      {agreement && <AgreementPanel agreement={agreement} />}

      {cohort.length === 0 ? (
        <p style={panel}>
          Nobody on your caseload yet. Add a learner and they will appear here — you will see
          their progress once they choose to share it with you.
        </p>
      ) : (
        <CohortTable members={cohort} />
      )}
    </section>
  );
}

function CohortTable({ members }: { members: CohortMember[] }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '44rem' }}>
        <caption style={{ textAlign: 'left', padding: '.5rem 0', color: 'var(--colour-fg-muted)' }}>
          Learners on your caseload. Progress is shown only where a learner has chosen to share it.
        </caption>
        <thead>
          <tr>
            {['Learner', 'Sharing', 'Phrases started', 'Due today', 'Interviews', 'Last practised'].map(
              (heading) => (
                <th key={heading} scope="col" style={cell}>
                  {heading}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.learner_user_id}>
              <th scope="row" style={{ ...cell, fontWeight: 700 }}>
                {member.display_name}
              </th>

              <td style={cell}>
                {member.shared ? (
                  'Yes'
                ) : (
                  // Explained, not blank. The trainer needs to know this is a
                  // choice, not a fault or a bug.
                  <span>
                    Not yet
                    <span className="visually-hidden"> — this learner has not chosen to share</span>
                  </span>
                )}
              </td>

              {/* An em dash reads as "not shared" to a sighted user; the hidden
                  text says so properly for a screen reader. */}
              <Metric value={member.cards_started} />
              <Metric value={member.cards_due} />
              <Metric value={member.interviews_completed} />

              <td style={cell}>
                {member.shared ? (
                  member.last_active_at ? (
                    new Date(member.last_active_at).toLocaleDateString()
                  ) : (
                    'Not started'
                  )
                ) : (
                  <NotShared />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ value }: { value: number | null }) {
  return <td style={cell}>{value === null ? <NotShared /> : value}</td>;
}

function NotShared() {
  return (
    <>
      <span aria-hidden="true">—</span>
      <span className="visually-hidden">Not shared</span>
    </>
  );
}

function AgreementPanel({ agreement }: { agreement: Agreement }) {
  const percent = Math.round(agreement.agreement * 100);
  const target = Math.round(agreement.target_agreement * 100);
  const below = agreement.scores > 0 && agreement.agreement < agreement.target_agreement;

  return (
    <section aria-labelledby="agreement-heading" style={{ ...panel, marginBottom: '1.5rem' }}>
      <h3 id="agreement-heading" style={{ marginTop: 0, fontSize: '1.125rem' }}>
        How often you agree with the AI
      </h3>

      {agreement.scores === 0 ? (
        <p style={{ margin: 0, color: 'var(--colour-fg-muted)' }}>
          No scores yet. This will fill in once your learners complete interviews.
        </p>
      ) : (
        <>
          {/* A meter, with its numbers also written out — a bar alone means
              nothing to a screen reader, and a percentage alone means little
              without the counts behind it. */}
          <p style={{ margin: '0 0 .5rem', fontSize: '1.5rem', fontWeight: 700 }}>
            {percent}%
          </p>
          <p style={{ margin: 0 }}>
            You accepted {agreement.scores - agreement.overridden} of {agreement.scores} scores,
            and changed {agreement.overridden}.
          </p>
          {below && (
            <p style={{ marginBottom: 0 }}>
              <strong>Below the {target}% target.</strong> {agreement.note}
            </p>
          )}
        </>
      )}
    </section>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  padding: 'var(--space-md, 1rem)',
} as const;

const cell = {
  textAlign: 'left',
  padding: '.6rem .75rem',
  borderBottom: '1px solid var(--colour-border)',
} as const;

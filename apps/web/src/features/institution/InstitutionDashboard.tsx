/**
 * Institution analytics (M14).
 *
 * The hard part of this screen is not the numbers — it is the gaps.
 *
 * Wherever a figure is withheld the screen says WHY, in the same visual weight
 * as the figures themselves. An institution that sees an unexplained blank
 * assumes a bug and asks us to remove the protection; one that reads
 * "withheld: fewer than 5 learners" understands it is working as intended and
 * stops asking.
 *
 * Nothing here identifies anyone. There is no drill-down, no filter, and no
 * export of individuals — because arbitrary narrowing is how aggregate data
 * gets turned back into people.
 */
import { useCallback, useEffect, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

export interface Cell {
  label: string;
  count: number | null;
  suppressed: boolean;
  reason: string;
}

export interface CohortReport {
  learners: Cell;
  enrolled: number;
  active_last_30_days: Cell;
  completed_an_interview: Cell;
  reliable_phrases: Record<string, Cell>;
  modality_mix: Record<string, Cell>;
  engagement_rate: number | null;
  notes: string[];
}

const MODALITY_LABEL: Record<string, string> = {
  captioned_text: 'Text and captions',
  audio: 'Spoken audio',
  easy_read: 'Easy-Read',
  pictograph: 'Picture symbols',
  isl: 'Indian Sign Language',
  unknown: 'Not yet set',
};

export function InstitutionDashboard({ token }: { token: string }) {
  const announce = useAnnounce();
  const [report, setReport] = useState<CohortReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const response = await fetch(`${BASE_URL}/institution/cohort`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);

    if (!response?.ok) {
      setError('We could not load the report just now. Please try again shortly.');
      return;
    }

    const body = (await response.json()) as CohortReport;
    setReport(body);
    announce('Cohort report loaded.');
  }, [announce, token]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <p data-testid="institution-error" role="alert" style={panel}>
        {error}
      </p>
    );
  }

  if (!report) return <p role="status">Loading the report…</p>;

  return (
    <section aria-labelledby="cohort-heading">
      <h2 id="cohort-heading" style={{ marginTop: 0 }}>
        Cohort report
      </h2>
      <p style={{ color: 'var(--colour-fg-muted)', maxWidth: '62ch' }}>
        Aggregated and anonymised. No individual learner can be identified here, and there is
        deliberately no way to narrow this to a smaller group.
      </p>

      <ul
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(13rem, 1fr))',
          gap: 'var(--space-md, 1rem)',
          listStyle: 'none',
          padding: 0,
          margin: '0 0 var(--space-lg, 1.5rem)',
        }}
      >
        <Figure label="Learners enrolled" value={report.enrolled} />
        <CellFigure label="Included in reporting" cell={report.learners} />
        <CellFigure label="Practised in the last 30 days" cell={report.active_last_30_days} />
        <CellFigure label="Completed an interview" cell={report.completed_an_interview} />
        <Figure
          label="Engagement"
          value={report.engagement_rate === null ? null : `${report.engagement_rate}%`}
          reason={
            report.engagement_rate === null
              ? 'Withheld: the group is too small to publish a rate safely.'
              : undefined
          }
        />
      </ul>

      <Breakdown
        heading="Phrases held reliably"
        cells={report.reliable_phrases}
        describe={(label) => `${label} phrases`}
      />

      <Breakdown
        heading="How learners communicate"
        cells={report.modality_mix}
        describe={(label) => MODALITY_LABEL[label] ?? label}
        note="This is the most identifying breakdown in the report, so it is suppressed most readily."
      />

      {report.notes.length > 0 && (
        <section aria-labelledby="notes-heading" style={{ ...panel, marginTop: 'var(--space-lg, 1.5rem)' }}>
          <h3 id="notes-heading" style={{ marginTop: 0, fontSize: '1.05rem' }}>
            About these figures
          </h3>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {report.notes.map((note) => (
              <li key={note} style={{ marginBottom: '.35rem' }}>
                {note}
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}

function Figure({
  label,
  value,
  reason,
}: {
  label: string;
  value: number | string | null;
  reason?: string;
}) {
  return (
    <li style={panel}>
      <p style={{ margin: 0, fontSize: '2rem', fontWeight: 700 }} aria-hidden="true">
        {value ?? '—'}
      </p>
      <p style={{ margin: '.25rem 0 0' }}>
        {/* The whole figure, said once, as a sentence. The visible number, the
            visible label and the visible reason are each aria-hidden, so a
            screen reader hears this and not three fragments — and hears the
            reason exactly once rather than twice. */}
        <span className="visually-hidden">
          {`${label}: ${value ?? 'withheld'}.${reason ? ` ${reason}` : ''}`}
        </span>
        <span aria-hidden="true">{label}</span>
      </p>
      {reason && (
        <p
          aria-hidden="true"
          style={{ margin: '.35rem 0 0', fontSize: '.85rem', color: 'var(--colour-fg-muted)' }}
        >
          {reason}
        </p>
      )}
    </li>
  );
}

function CellFigure({ label, cell }: { label: string; cell: Cell }) {
  return (
    <Figure
      label={label}
      value={cell.count}
      // The reason is shown at the same weight as a number would be. A blank
      // with no explanation reads as a bug.
      reason={cell.suppressed ? cell.reason : undefined}
    />
  );
}

function Breakdown({
  heading,
  cells,
  describe,
  note,
}: {
  heading: string;
  cells: Record<string, Cell>;
  describe: (label: string) => string;
  note?: string;
}) {
  const entries = Object.entries(cells);
  if (entries.length === 0) return null;

  return (
    <section aria-labelledby={`bd-${heading}`} style={{ marginBottom: 'var(--space-lg, 1.5rem)' }}>
      <h3 id={`bd-${heading}`}>{heading}</h3>
      {note && <p style={{ color: 'var(--colour-fg-muted)', marginTop: 0 }}>{note}</p>}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', minWidth: '26rem' }}>
          <tbody>
            {entries.map(([label, cell]) => (
              <tr key={label}>
                <th scope="row" style={cellStyle}>
                  {describe(label)}
                </th>
                <td style={cellStyle}>
                  {cell.suppressed ? (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="visually-hidden">Withheld</span>
                    </>
                  ) : (
                    cell.count
                  )}
                </td>
                <td style={{ ...cellStyle, color: 'var(--colour-fg-muted)', fontSize: '.9rem' }}>
                  {cell.suppressed ? cell.reason : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  padding: 'var(--space-md, 1rem)',
} as const;

const cellStyle = {
  textAlign: 'left',
  padding: '.5rem .75rem',
  borderBottom: '1px solid var(--colour-border)',
} as const;

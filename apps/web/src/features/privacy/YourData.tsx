/**
 * Your data (M17) — export and erasure, self-service.
 *
 * Both rights existed in the API and neither was reachable, which made
 * "self-service erasure" a claim rather than a fact. A right a learner cannot
 * find is a right they have to email somebody about, and a right you have to
 * email somebody about is not one a disabled learner can reliably exercise.
 *
 * DELETION IS NOT DISCOURAGED HERE
 * -------------------------------
 * The standard pattern — type DELETE to confirm — excludes people with
 * literacy difficulties and people using switch access, which is to say it
 * excludes exactly this product's users. It is also, in most products, a dark
 * pattern wearing a safety jacket: friction dressed as protection.
 *
 * What is used instead: two plain steps, the consequence stated once in short
 * sentences, and a cancel that is no harder to reach than the confirm. Nothing
 * here pleads, warns about "losing your progress", or offers an alternative to
 * deleting. The learner asked.
 */
import { useCallback, useState } from 'react';

import { useAnnounce } from '@/a11y/Announcer';

const BASE_URL = import.meta.env['VITE_API_URL'] ?? 'http://localhost:8000';

type Stage = 'idle' | 'confirming' | 'deleting' | 'deleted' | 'error';

export function YourData({ token, onErased }: { token: string; onErased?: () => void }) {
  const announce = useAnnounce();
  const [stage, setStage] = useState<Stage>('idle');
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const download = useCallback(async () => {
    setDownloading(true);
    setDownloadError(null);

    const response = await fetch(`${BASE_URL}/export/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);

    if (!response?.ok) {
      setDownloadError('We could not make your file just now. Please try again shortly.');
      setDownloading(false);
      return;
    }

    const text = await response.text();
    saveFile(text, 'samvaad-my-data.json');
    setDownloading(false);
    announce('Your file has been saved.');
  }, [announce, token]);

  const erase = useCallback(async () => {
    setStage('deleting');

    const response = await fetch(`${BASE_URL}/auth/me`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);

    if (!response?.ok) {
      setStage('error');
      return;
    }

    setStage('deleted');
    announce('Everything has been deleted.');
    onErased?.();
  }, [announce, onErased, token]);

  if (stage === 'deleted') {
    return (
      <section style={panel}>
        <h2 style={{ marginTop: 0 }}>Everything has been deleted</h2>
        <p>There is nothing left about you here.</p>
        <p>Thank you for practising with us.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="data-heading">
      <h2 id="data-heading" style={{ marginTop: 0 }}>
        Your data
      </h2>

      <section aria-labelledby="download-heading" style={{ ...panel, marginBottom: '1.5rem' }}>
        <h3 id="download-heading" style={{ marginTop: 0 }}>
          Get a copy
        </h3>
        <p style={{ maxWidth: '58ch' }}>
          You can download everything we hold about you. It is one file. You can keep it, or give
          it to someone else.
        </p>
        <button type="button" onClick={() => void download()} disabled={downloading} style={button}>
          {downloading ? 'Making your file…' : 'Download my data'}
        </button>
        {downloadError && (
          <p data-testid="download-error" role="alert" style={{ marginBottom: 0 }}>
            {downloadError}
          </p>
        )}
      </section>

      <section aria-labelledby="delete-heading" style={panel}>
        <h3 id="delete-heading" style={{ marginTop: 0 }}>
          Delete everything
        </h3>

        {stage === 'idle' && (
          <>
            <p style={{ maxWidth: '58ch' }}>
              You can delete everything about you. You do not have to give a reason. You do not
              have to ask anyone.
            </p>
            <button type="button" onClick={() => setStage('confirming')} style={button}>
              Delete everything about me
            </button>
          </>
        )}

        {(stage === 'confirming' || stage === 'deleting') && (
          <div role="group" aria-labelledby="confirm-heading">
            <p id="confirm-heading" style={{ fontWeight: 600 }}>
              Are you sure?
            </p>
            {/* Stated once, plainly. Not repeated to wear the learner down. */}
            <p>This deletes your practice, your settings and your answers.</p>
            <p>It cannot be undone.</p>
            <p>You may want to download your data first.</p>

            <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
              {/* Cancel first in the reading and tab order — a switch user
                  scanning left to right reaches "No" before "Yes". */}
              <button type="button" onClick={() => setStage('idle')} style={button}>
                No, keep my data
              </button>
              <button
                type="button"
                onClick={() => void erase()}
                disabled={stage === 'deleting'}
                style={button}
              >
                {stage === 'deleting' ? 'Deleting…' : 'Yes, delete everything'}
              </button>
            </div>
          </div>
        )}

        {stage === 'error' && (
          <>
            <p data-testid="delete-error" role="alert">
              We could not delete your data just now. Nothing has been changed. Please try again
              shortly.
            </p>
            <button type="button" onClick={() => setStage('confirming')} style={button}>
              Try again
            </button>
          </>
        )}
      </section>
    </section>
  );
}

/**
 * Saves the export without a round trip to a server-rendered download page.
 *
 * Guarded because jsdom has no `URL.createObjectURL`, and an unguarded call
 * throws inside the click handler — which is how the read-aloud button on the
 * onboarding screen broke.
 */
function saveFile(contents: string, filename: string): void {
  if (typeof URL?.createObjectURL !== 'function') return;

  try {
    const url = URL.createObjectURL(new Blob([contents], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch {
    // A failed save is not worth breaking the screen over; the learner can
    // press the button again.
  }
}

const panel = {
  background: 'var(--colour-surface)',
  border: '1px solid var(--colour-border)',
  borderRadius: 'var(--radius-md, 8px)',
  padding: 'var(--space-md, 1rem)',
} as const;

const button = {
  minHeight: '3rem',
  padding: '.75rem 1.25rem',
  fontSize: '1.05rem',
  borderRadius: 'var(--radius-md, 8px)',
  border: '1px solid var(--colour-border)',
  background: 'var(--colour-surface)',
  color: 'var(--colour-fg)',
  cursor: 'pointer',
} as const;

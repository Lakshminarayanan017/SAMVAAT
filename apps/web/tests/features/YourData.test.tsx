/**
 * Export and erasure, on screen.
 *
 * Most of these are copy tests, which is unusual and deliberate. The API
 * behaviour is tested in apps/api; what is left for the client to get wrong is
 * entirely a matter of wording and pressure — whether the learner is nudged out
 * of deleting, whether the consequence is stated once or repeated at them, and
 * whether the confirm is easier to reach than the cancel.
 *
 * Those are the things that quietly turn a right into a maze, and they are
 * invisible to every other kind of test.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { YourData } from '@/features/privacy/YourData';
import { page } from '../helpers';

function stubApi({ ok = true } = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok,
      status: ok ? 200 : 503,
      text: async () => '{"export_version":1}',
      json: async () => ({ erased: true }),
    })),
  );
}

function setup(onErased?: () => void) {
  render(
    <AnnouncerProvider>
      <YourData token="learner-token" onErased={onErased} />
    </AnnouncerProvider>,
  );
}

beforeEach(() => stubApi());
afterEach(() => vi.unstubAllGlobals());

describe('getting a copy', () => {
  it('offers a download', async () => {
    setup();
    expect(page().getByRole('button', { name: /download my data/i })).toBeInTheDocument();
  });

  it('says what the learner can do with the file', async () => {
    setup();
    expect(page().getByText(/give it to someone else/i)).toBeInTheDocument();
  });

  it('does not throw when the browser cannot save a blob', async () => {
    /* jsdom has no URL.createObjectURL. An unguarded call throws inside the
       click handler and takes the screen down — which is exactly how the
       read-aloud button on the onboarding screen broke. */
    setup();
    await userEvent.click(page().getByRole('button', { name: /download my data/i }));

    await waitFor(() =>
      expect(page().getByRole('button', { name: /download my data/i })).toBeEnabled(),
    );
    expect(screen.queryByTestId('download-error')).not.toBeInTheDocument();
  });

  it('says so plainly when the file cannot be made', async () => {
    stubApi({ ok: false });
    setup();

    await userEvent.click(page().getByRole('button', { name: /download my data/i }));

    await waitFor(() =>
      expect(screen.getByTestId('download-error')).toHaveTextContent(/could not make your file/i),
    );
  });
});

describe('deleting everything', () => {
  it('asks once before deleting', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));

    expect(page().getByText(/are you sure/i)).toBeInTheDocument();
  });

  it('does not delete anything until the learner confirms', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));

    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
  });

  it('deletes when confirmed', async () => {
    const onErased = vi.fn();
    setup(onErased);

    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    await userEvent.click(page().getByRole('button', { name: /yes, delete everything/i }));

    await waitFor(() => expect(onErased).toHaveBeenCalled());
    expect(page().getByText(/nothing left about you/i)).toBeInTheDocument();
  });

  it('lets the learner back out', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    await userEvent.click(page().getByRole('button', { name: /no, keep my data/i }));

    expect(page().queryByText(/are you sure/i)).not.toBeInTheDocument();
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
  });

  it('says nothing changed when the deletion fails', async () => {
    /* The worst possible message here is an ambiguous one. A learner who
       believes their data might be half-deleted has no way to find out. */
    stubApi({ ok: false });
    setup();

    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    await userEvent.click(page().getByRole('button', { name: /yes, delete everything/i }));

    await waitFor(() =>
      expect(screen.getByTestId('delete-error')).toHaveTextContent(/nothing has been changed/i),
    );
  });
});

describe('the learner is not talked out of it', () => {
  async function confirmScreen() {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    return document.querySelector('[data-samvaad-content]')?.textContent ?? '';
  }

  it('does not plead, warn about lost progress, or offer an alternative', async () => {
    const text = await confirmScreen();

    for (const pattern of [
      /are you really sure/i,
      /you will lose/i,
      /lose all your progress/i,
      /instead,? (why not|you could)/i,
      /we will miss you/i,
      /take a break instead/i,
      /pause your account/i,
    ]) {
      expect(text).not.toMatch(pattern);
    }
  });

  it('states the consequence once, not repeatedly', async () => {
    const text = await confirmScreen();
    expect(text.match(/cannot be undone/gi) ?? []).toHaveLength(1);
  });

  it('puts cancel before confirm in the tab order', async () => {
    /* A switch user scans in DOM order. Reaching "Yes, delete everything"
       before "No, keep my data" makes the destructive option the default for
       exactly the people least able to correct a mistake. */
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));

    const labels = page()
      .getAllByRole('button')
      .map((element) => element.textContent ?? '');
    const cancel = labels.findIndex((label) => /no, keep/i.test(label));
    const confirm = labels.findIndex((label) => /yes, delete/i.test(label));

    expect(cancel).toBeGreaterThanOrEqual(0);
    expect(cancel).toBeLessThan(confirm);
  });

  it('makes cancel no harder to press than confirm', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));

    const cancel = page().getByRole('button', { name: /no, keep my data/i });
    const confirm = page().getByRole('button', { name: /yes, delete everything/i });

    // Same styling, so neither is visually demoted into a hard-to-hit link.
    expect(cancel.tagName).toBe(confirm.tagName);
    expect(cancel.getAttribute('style')).toBe(confirm.getAttribute('style'));
  });

  it('never asks the learner to type a word to confirm', async () => {
    /* "Type DELETE to confirm" excludes people with literacy difficulties and
       people using switch access — which is to say, this product's users. */
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));

    expect(page().queryAllByRole('textbox')).toHaveLength(0);
  });

  it('does not demand a reason', async () => {
    setup();
    expect(page().getByText(/do not have to give a reason/i)).toBeInTheDocument();
  });
});

describe('what the learner is told afterwards', () => {
  it('confirms the deletion happened, plainly', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    await userEvent.click(page().getByRole('button', { name: /yes, delete everything/i }));

    await waitFor(() =>
      expect(page().getByText(/everything has been deleted/i)).toBeInTheDocument(),
    );
  });

  it('does not guilt the learner on the way out', async () => {
    setup();
    await userEvent.click(page().getByRole('button', { name: /delete everything about me/i }));
    await userEvent.click(page().getByRole('button', { name: /yes, delete everything/i }));

    await waitFor(() => expect(page().getByText(/nothing left about you/i)).toBeInTheDocument());

    const text = document.querySelector('[data-samvaad-content]')?.textContent ?? '';
    expect(text).not.toMatch(/sorry to see you go|come back|changed your mind/i);
  });
});

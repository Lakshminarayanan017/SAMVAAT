/**
 * Dialog and Sheet — focus-managed overlays.
 *
 * Built on the native `<dialog>` element rather than a div with `role="dialog"`,
 * because the platform gives four things correctly and for free that hand-rolled
 * modals routinely get wrong: focus trapping, inertness of the page behind,
 * Escape to close, and the top layer (so no z-index arithmetic).
 *
 * WHAT IS ADDED ON TOP
 * --------------------
 * 1. **Focus restoration.** `showModal()` moves focus in; it does not put it
 *    back. A learner who opens a dialog from a button and closes it must land
 *    back on that button, not at the top of the document — for a switch user
 *    starting the scan again is a genuine cost.
 * 2. **An always-present close control.** Escape is not discoverable, and it is
 *    unavailable to a switch user driving a two-button interface.
 * 3. **A labelled heading**, wired via `aria-labelledby`, so the dialog
 *    announces what it is on open.
 *
 * `Sheet` is the same machinery anchored to the bottom edge — a phone-shaped
 * presentation, not a different behaviour.
 */
import { useEffect, useRef, type ReactNode } from 'react';

import { Button } from './Button';

export interface OverlayProps {
  open: boolean;
  onClose: () => void;
  title: string;
  /** Label for the close control. Defaults to "Close". */
  closeLabel?: string;
  children: ReactNode;
}

function useDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    // jsdom implements <dialog> only partially depending on version, so both
    // calls are guarded. A missing showModal must not take the screen down.
    if (open && !dialog.open) {
      opener.current = document.activeElement;
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
    } else if (!open && dialog.open) {
      if (typeof dialog.close === 'function') dialog.close();
      else dialog.removeAttribute('open');

      // Put focus back where the learner left it.
      if (opener.current instanceof HTMLElement) opener.current.focus();
    }
  }, [open]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;

    // The native Escape key fires `cancel`; the state above must follow it or
    // the dialog closes visually while the component still thinks it is open.
    const onCancel = (event: Event) => {
      event.preventDefault();
      onClose();
    };
    dialog.addEventListener('cancel', onCancel);
    return () => dialog.removeEventListener('cancel', onCancel);
  }, [onClose]);

  return ref;
}

export function Dialog({ open, onClose, title, closeLabel = 'Close', children }: OverlayProps) {
  const ref = useDialog(open, onClose);
  const titleId = `dialog-title-${title.replace(/\W+/g, '-').toLowerCase()}`;

  return (
    <dialog
      ref={ref}
      data-ui="dialog"
      aria-labelledby={titleId}
      style={{
        border: '2px solid var(--border-strong)',
        borderRadius: 'var(--radius-lg, 14px)',
        background: 'var(--surface-raised)',
        color: 'var(--text-primary)',
        padding: 'var(--space-lg, 1.5rem)',
        maxInlineSize: 'min(34rem, 92vw)',
        inlineSize: '100%',
      }}
    >
      <h2 id={titleId} style={{ marginBlockStart: 0 }}>
        {title}
      </h2>
      {children}
      <div style={{ marginBlockStart: 'var(--space-md, 1rem)' }}>
        <Button variant="secondary" onRaised onClick={onClose}>
          {closeLabel}
        </Button>
      </div>
    </dialog>
  );
}

export function Sheet({ open, onClose, title, closeLabel = 'Close', children }: OverlayProps) {
  const ref = useDialog(open, onClose);
  const titleId = `sheet-title-${title.replace(/\W+/g, '-').toLowerCase()}`;

  return (
    <dialog
      ref={ref}
      data-ui="sheet"
      aria-labelledby={titleId}
      style={{
        border: '2px solid var(--border-strong)',
        borderStartStartRadius: 'var(--radius-xl, 18px)',
        borderStartEndRadius: 'var(--radius-xl, 18px)',
        background: 'var(--surface-raised)',
        color: 'var(--text-primary)',
        padding: 'var(--space-lg, 1.5rem)',
        inlineSize: 'min(40rem, 100vw)',
        marginBlockEnd: 0,
        marginInline: 'auto',
        // Capped so a tall sheet scrolls internally rather than pushing its own
        // close button off the bottom of the screen.
        maxBlockSize: '85vh',
      }}
    >
      <h2 id={titleId} style={{ marginBlockStart: 0 }}>
        {title}
      </h2>
      {children}
      <div style={{ marginBlockStart: 'var(--space-md, 1rem)' }}>
        <Button variant="secondary" onRaised onClick={onClose}>
          {closeLabel}
        </Button>
      </div>
    </dialog>
  );
}

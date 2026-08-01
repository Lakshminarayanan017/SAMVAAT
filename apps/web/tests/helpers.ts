/**
 * Query helpers.
 *
 * `page()` scopes a query to the rendered application, excluding the global
 * live regions. Those regions legitimately duplicate whatever was just
 * announced, so an unscoped `getByText` finds two copies of every status
 * message — which is a test artefact, not a bug in the screen.
 *
 * Use `page().getByText(...)` when asserting on something the app also
 * announces. Use `screen` when asserting on the announcement itself.
 */
import { within } from '@testing-library/react';

export function page() {
  const root = document.querySelector<HTMLElement>('[data-samvaad-content]');
  if (!root) {
    throw new Error(
      'No [data-samvaad-content] found. Wrap the component under test in <AnnouncerProvider>.',
    );
  }
  return within(root);
}

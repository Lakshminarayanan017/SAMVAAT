import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import type { ContentBlock } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ChannelComparison } from '@/features/channel-comparison/ChannelComparison';
import { CapabilitiesProvider } from '@/services/capabilities';
import { applyTheme } from '@/design-system/tokens';
import './styles/global.css';

// The real Workplace Language Bank, built from packages/content. Until the
// content API lands the client reads the built artefact directly, so the demo
// always shows exactly what the validator checked.
// Run `npm run content:build` first — this import fails loudly otherwise.
//
// KNOWN ISSUE, must be fixed before the pilot: this inlines all 226 blocks into
// the bundle (~270kB raw, ~80kB gzipped, and it only grows as ISL and phoneme
// data land). Our learners are on entry-level Android and low bandwidth, so
// shipping the whole corpus up front is exactly the wrong trade. M15 replaces
// this with a fetch into IndexedDB that prefetches only the next ~50 due cards.
import blocks from '../../../packages/content/dist/blocks.json';

// Apply a theme before first paint so there is no flash of the wrong contrast.
// The ProfileProvider re-applies it from the learner's profile once mounted.
applyTheme({
  colourScheme: window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
  contrastTheme: window.matchMedia?.('(prefers-contrast: more)').matches
    ? 'high_contrast'
    : 'standard',
  motionReduced: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
});

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <CapabilitiesProvider>
      <AnnouncerProvider>
        <a href="#main" className="skip-link">
          Skip to main content
        </a>
        <ChannelComparison blocks={blocks as unknown as ContentBlock[]} />
      </AnnouncerProvider>
    </CapabilitiesProvider>
  </StrictMode>,
);

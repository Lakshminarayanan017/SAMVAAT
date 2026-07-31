import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import type { ContentBlock } from '@samvaad/contracts';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { ChannelComparison } from '@/features/channel-comparison/ChannelComparison';
import { applyTheme } from '@/design-system/tokens';
import './styles/global.css';

// Until the content API lands (M3) the comparison view runs on the same fixture
// the contract validator checks, so the demo can never drift from the contract.
import blockFixture from '../../../packages/contracts/fixtures/valid/content-block/phrase-repeat-request.json';

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
    <AnnouncerProvider>
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <ChannelComparison block={blockFixture as unknown as ContentBlock} />
    </AnnouncerProvider>
  </StrictMode>,
);

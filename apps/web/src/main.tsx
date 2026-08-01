import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { AnnouncerProvider } from '@/a11y/Announcer';
import { AppShell } from '@/routes/AppShell';
import { CapabilitiesProvider } from '@/services/capabilities';
import { applyTheme } from '@/design-system/tokens';
import './styles/global.css';
import './styles/game.css';
import './ui/ui.css';



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
        <AppShell />
      </AnnouncerProvider>
    </CapabilitiesProvider>
  </StrictMode>,
);

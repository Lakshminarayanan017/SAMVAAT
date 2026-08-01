// `vitest/config` rather than `vite`, so the `test` block below is typed.
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // The app shell only. The phrase bank lives in IndexedDB, not in the
      // precache — 226 blocks in a service-worker manifest would reintroduce
      // the bundle-size problem this module exists to fix.
      workbox: {
        globPatterns: ['**/*.{js,css,html,woff2}'],
        // The API is never precached. Stale learner data is worse than no
        // learner data, and the outbox already covers writes.
        navigateFallbackDenylist: [/^\/api/],
      },
      manifest: {
        name: 'SAMVAAD',
        short_name: 'SAMVAAD',
        description: 'Workplace communication practice.',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#005a9c',
        // Installable on entry-level Android, which is where the learners are.
        icons: [],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@samvaad/contracts': fileURLToPath(new URL('../../packages/contracts/src/index.ts', import.meta.url)),
    },
  },
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    globals: true,
    include: ['tests/**/*.{test,spec}.{ts,tsx}'],
  },
});

import { fileURLToPath, URL } from 'node:url';
// `vitest/config` re-exports Vite's defineConfig with the `test` block typed.
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    // Node environment: there is no DOM, so component and hook tests cannot render.
    // Keep decisions in pure functions (see features/tutor/episodeRules.ts) so they
    // are testable here. To test components, add jsdom + @testing-library/react
    // and widen `include` to *.test.tsx; a .tsx test would fail on first render today.
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});

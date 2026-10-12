/** Environment configuration. See `.env.example`. */

export type TransportMode = 'mock' | 'direct' | 'express';

function readMode(): TransportMode {
  const raw = import.meta.env.VITE_TUTOR_MODE;
  if (raw === 'mock' || raw === 'direct' || raw === 'express') return raw;
  // Default to `mock` so a fresh clone runs with no backend (F1-F9).
  return 'mock';
}

export const env = {
  mode: readMode(),
  tutorUrl: import.meta.env.VITE_TUTOR_URL ?? 'http://localhost:8001',
  expressBase: import.meta.env.VITE_EXPRESS_BASE ?? '/api',
  isDev: import.meta.env.DEV,
} as const;

/** Max cycles, mirrored from the service config for display only
 *  ("cycle 1 of 2"). The service remains the authority. */
export const DISPLAY_MAX_CYCLES = 2;

/**
 * Standalone entry point. THIS IS THE ONLY FILE SPECIFIC TO RUNNING ALONE.
 *
 * To integrate into the team's React app (10_DECISIONS.md Q3): import
 * `TutorFeature` from `features/tutor`, mount it on a route, and delete this
 * file. Nothing else changes.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { TutorFeatureApp as TutorFeature } from './features/tutor/TutorFeatureApp';
import './index.css';

const container = document.getElementById('root');
if (!container) throw new Error('Root element #root not found');

createRoot(container).render(
  <StrictMode>
    <TutorFeature />
  </StrictMode>,
);

import { useState } from 'react';
import { DashboardView } from './features/dashboard/DashboardView';
import { TutorFeatureApp } from './features/tutor/TutorFeatureApp';

export type AppViewMode = 'dashboard' | 'tutor';

export function App() {
  // Default to 'dashboard' as requested: "create dashboard only ui"
  const [view, setView] = useState<AppViewMode>('dashboard');

  return (
    <div className="relative min-h-screen w-full">
      {view === 'dashboard' ? (
        <DashboardView onOpenTutor={() => setView('tutor')} />
      ) : (
        <div className="relative">
          {/* Quick back to dashboard switcher bar */}
          <div className="sticky top-0 z-30 flex items-center justify-between border-b border-[#e2e8f0] bg-white px-4 py-2 text-xs font-semibold text-[#64748b] shadow-2xs">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
              <span>Interactive Tutoring Session</span>
            </div>
            <button
              type="button"
              onClick={() => setView('dashboard')}
              className="flex items-center gap-1.5 rounded-lg border border-[#bae6fd] bg-[#f0f9ff] px-3 py-1 font-bold text-[#0369a1] hover:bg-[#e0f2fe] transition-colors"
            >
              <span>&larr; Back to Dashboard</span>
            </button>
          </div>
          <TutorFeatureApp />
        </div>
      )}
    </div>
  );
}

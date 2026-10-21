interface DashboardHeaderProps {
  isPopulatedState: boolean;
  onToggleDataState: (populated: boolean) => void;
  onStartPractice: () => void;
  weakTopicsCount: number;
}

export function DashboardHeader({
  isPopulatedState,
  onToggleDataState,
  onStartPractice,
  weakTopicsCount,
}: DashboardHeaderProps) {
  return (
    <header className="border-b border-[#e2e8f0] bg-white px-6 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {/* Title and Subtitle */}
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-extrabold tracking-tight text-[#1e293b]">
              Student Learning & Pedagogy Dashboard
            </h1>
            <span className="rounded-full bg-[#e0f2fe] px-2.5 py-0.5 text-xs font-bold text-[#0369a1]">
              Live Analytics
            </span>
          </div>
          <p className="mt-1 text-sm text-[#64748b]">
            Comprehension diagnostics, 3-strategy weakness detector, and personalized teaching effectiveness.
          </p>
        </div>

        {/* Controls and Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* State Switcher (Exact Screenshot vs Populated Exploration) */}
          <div className="flex items-center rounded-xl border border-[#d7e4ed] bg-[#f8fafc] p-1 text-xs font-semibold shadow-xs">
            <button
              type="button"
              onClick={() => onToggleDataState(false)}
              className={`rounded-lg px-3 py-1.5 transition-all ${
                !isPopulatedState
                  ? 'bg-white text-[#0369a1] shadow-xs font-bold'
                  : 'text-[#64748b] hover:text-[#1e293b]'
              }`}
              title="Matches the uploaded screenshot exactly"
            >
              Exact Image State
            </button>
            <button
              type="button"
              onClick={() => onToggleDataState(true)}
              className={`rounded-lg px-3 py-1.5 transition-all ${
                isPopulatedState
                  ? 'bg-white text-[#0369a1] shadow-xs font-bold'
                  : 'text-[#64748b] hover:text-[#1e293b]'
              }`}
              title="Preview with active learning history & effectiveness data"
            >
              Populated Session
            </button>
          </div>

          {/* Quick Practice Button */}
          <button
            type="button"
            onClick={onStartPractice}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#0284c7] to-[#0369a1] px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:from-[#0369a1] hover:to-[#075985]"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>Practice Weak Topic ({weakTopicsCount})</span>
          </button>
        </div>
      </div>
    </header>
  );
}

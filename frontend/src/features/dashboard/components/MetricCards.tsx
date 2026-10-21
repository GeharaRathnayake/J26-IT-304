import type { DashboardOverviewMetrics } from '../types';

interface MetricCardsProps {
  metrics: DashboardOverviewMetrics;
}

export function MetricCards({ metrics }: MetricCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* 1. CURRENT LEVEL */}
      <div className="flex flex-col justify-between rounded-2xl border border-[#e2e8f0] bg-white p-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)] transition-all hover:border-[#cbd5e1] hover:shadow-sm">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-extrabold tracking-wider text-[#71828f] uppercase">
              Current Level
            </span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#ecfdf5] text-[#059669]">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
          </div>
          <div className="mt-2 text-3xl font-extrabold text-[#059669]">
            {metrics.currentLevel}
          </div>
        </div>
        <p className="mt-3 text-xs font-medium text-[#8da0ad]">
          {metrics.levelSubtext}
        </p>
      </div>

      {/* 2. CONCEPTS LEARNED */}
      <div className="flex flex-col justify-between rounded-2xl border border-[#e2e8f0] bg-white p-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)] transition-all hover:border-[#cbd5e1] hover:shadow-sm">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-extrabold tracking-wider text-[#71828f] uppercase">
              Concepts Learned
            </span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#f0f9ff] text-[#0284c7]">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2v20" />
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </div>
          </div>
          <div className="mt-2 text-3xl font-extrabold text-[#1e293b]">
            {metrics.conceptsLearned}
          </div>
        </div>
        <p className="mt-3 text-xs font-medium text-[#8da0ad]">
          {metrics.conceptsSubtext}
        </p>
      </div>

      {/* 3. WEAK TOPICS */}
      <div className="flex flex-col justify-between rounded-2xl border border-[#e2e8f0] bg-white p-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)] transition-all hover:border-[#cbd5e1] hover:shadow-sm">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-extrabold tracking-wider text-[#71828f] uppercase">
              Weak Topics
            </span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#fff1f2] text-[#e11d48]">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
          </div>
          <div className="mt-2 text-3xl font-extrabold text-[#1e293b]">
            {metrics.weakTopicsCount}
          </div>
        </div>
        <p className="mt-3 text-xs font-medium text-[#8da0ad]">
          {metrics.weakTopicsSubtext}
        </p>
      </div>

      {/* 4. HELPFUL STYLE */}
      <div className="flex flex-col justify-between rounded-2xl border border-[#e2e8f0] bg-white p-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)] transition-all hover:border-[#cbd5e1] hover:shadow-sm">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-extrabold tracking-wider text-[#71828f] uppercase">
              Helpful Style
            </span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#f5f3ff] text-[#7c3aed]">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2a10 10 0 1 0 10 10H12V2Z" />
                <path d="M12 12L2.5 7.5" />
                <path d="M12 12V22" />
              </svg>
            </div>
          </div>
          <div className="mt-2 text-3xl font-extrabold text-[#1e293b]">
            {metrics.helpfulStyle}
          </div>
        </div>
        <p className="mt-3 text-xs font-medium text-[#8da0ad]">
          {metrics.helpfulStyleSubtext}
        </p>
      </div>
    </div>
  );
}

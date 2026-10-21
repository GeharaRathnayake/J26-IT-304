import React from 'react';
import type { StudentDashboardProfile } from '../types';

interface MetricStatCardsProps {
  profile: StudentDashboardProfile;
  onScrollToWeakTopics?: () => void;
  onScrollToTeachingMethods?: () => void;
}

export const MetricStatCards: React.FC<MetricStatCardsProps> = ({
  profile,
  onScrollToWeakTopics,
  onScrollToTeachingMethods,
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. CURRENT LEVEL */}
      <div className="bg-white border border-[#dce8e5] hover:border-[#0ca58e]/40 rounded-3xl p-5 shadow-xs transition-all hover:shadow-md hover:shadow-teal-900/5 group">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-extrabold tracking-wider text-[#638983] uppercase">
            CURRENT LEVEL
          </span>
          <span className="w-8 h-8 rounded-xl bg-[#ecf7f4] text-[#0ca58e] flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
          </span>
        </div>
        <div className="text-2xl font-extrabold text-[#0ca58e] tracking-tight mb-1">
          {profile.currentLevel}
        </div>
        <p className="text-xs text-[#527771] font-medium leading-relaxed mb-3">
          {profile.levelBadge} â€¢ Advancing
        </p>
        {/* Progress bar */}
        <div className="w-full bg-[#ecf4f2] h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-[#0ca58e] to-[#0a8673] h-full rounded-full transition-all duration-500"
            style={{ width: `${profile.levelProgressPercent}%` }}
          />
        </div>
      </div>

      {/* 2. CONCEPTS LEARNED */}
      <div className="bg-white border border-[#dce8e5] hover:border-[#0ca58e]/40 rounded-3xl p-5 shadow-xs transition-all hover:shadow-md hover:shadow-teal-900/5 group">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-extrabold tracking-wider text-[#638983] uppercase">
            CONCEPTS LEARNED
          </span>
          <span className="w-8 h-8 rounded-xl bg-[#ecf7f4] text-[#0ca58e] flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </span>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-2xl font-extrabold text-[#11302b] tracking-tight">
            {profile.conceptsLearned}
          </span>
          <span className="text-xs font-semibold text-[#668b85]">
            / {profile.totalConceptsInCurriculum} Total
          </span>
        </div>
        <p className="text-xs text-[#527771] font-medium leading-relaxed mb-3">
          Understood in the voice tutor
        </p>
        {/* Progress bar */}
        <div className="w-full bg-[#ecf4f2] h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-[#0ca58e] to-[#34d399] h-full rounded-full transition-all duration-500"
            style={{
              width: `${(profile.conceptsLearned / profile.totalConceptsInCurriculum) * 100}%`,
            }}
          />
        </div>
      </div>

      {/* 3. WEAK TOPICS */}
      <div
        onClick={onScrollToWeakTopics}
        className="bg-white border border-[#dce8e5] hover:border-rose-300 rounded-3xl p-5 shadow-xs transition-all hover:shadow-md hover:shadow-rose-900/5 group cursor-pointer"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-extrabold tracking-wider text-[#638983] uppercase">
            WEAK TOPICS
          </span>
          <span className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </span>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-2xl font-extrabold text-rose-600 tracking-tight">
            {profile.weakTopicsCount}
          </span>
          <span className="text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
            Action needed
          </span>
        </div>
        <p className="text-xs text-[#527771] font-medium leading-relaxed mb-3">
          Needed â‰¥3 strategies to understand
        </p>
        {/* Flag indicator */}
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-rose-600 group-hover:underline">
          <span>Inspect weak topics</span>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* 4. HELPFUL STYLE */}
      <div
        onClick={onScrollToTeachingMethods}
        className="bg-white border border-[#dce8e5] hover:border-emerald-300 rounded-3xl p-5 shadow-xs transition-all hover:shadow-md hover:shadow-emerald-900/5 group cursor-pointer"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-extrabold tracking-wider text-[#638983] uppercase">
            HELPFUL STYLE
          </span>
          <span className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </span>
        </div>
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-2xl font-extrabold text-[#11302b] tracking-tight">
            {profile.topHelpfulStyleName}
          </span>
          <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            {profile.topHelpfulStyleSuccessRate}% Win
          </span>
        </div>
        <p className="text-xs text-[#527771] font-medium leading-relaxed mb-3">
          Style that worked most often
        </p>
        {/* Style link */}
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-[#0ca58e] group-hover:underline">
          <span>View prioritized methods</span>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
    </div>
  );
};

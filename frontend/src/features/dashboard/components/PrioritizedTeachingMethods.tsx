import { useState } from 'react';
import type { TeachingMethod } from '../types';

interface PrioritizedTeachingMethodsProps {
  methods: TeachingMethod[];
  onSelectMethod: (method: TeachingMethod) => void;
  onTestStrategy: (strategyId: string) => void;
}

export function PrioritizedTeachingMethods({
  methods,
  onSelectMethod,
  onTestStrategy,
}: PrioritizedTeachingMethodsProps) {
  const [selectedSort, setSelectedSort] = useState<'rank' | 'effectiveness'>('rank');

  const sortedMethods = [...methods].sort((a, b) => {
    if (selectedSort === 'rank') {
      return a.priorityRank - b.priorityRank;
    }
    return b.effectivenessPercent - a.effectivenessPercent;
  });

  return (
    <section className="space-y-4">
      {/* Section Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-[#1e293b]">
              Prioritized Personalized Teaching Methods
            </h2>
            <span className="rounded-full bg-[#fdf4ff] px-2.5 py-0.5 text-xs font-bold text-[#9333ea] border border-[#f5d0fe]">
              Adaptive Engine
            </span>
          </div>
          <p className="text-sm text-[#64748b]">
            Ranked pedagogy strategies tailored to the student&rsquo;s comprehension pace and cognitive responses.
          </p>
        </div>

        {/* Sort Filter */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="text-xs font-semibold text-[#8da0ad]">Order by:</span>
          <div className="inline-flex rounded-xl border border-[#d7e4ed] bg-white p-1 text-xs font-bold text-[#64748b] shadow-2xs">
            <button
              type="button"
              onClick={() => setSelectedSort('rank')}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                selectedSort === 'rank'
                  ? 'bg-[#0284c7] text-white shadow-2xs'
                  : 'hover:text-[#1e293b]'
              }`}
            >
              Priority Rank
            </button>
            <button
              type="button"
              onClick={() => setSelectedSort('effectiveness')}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                selectedSort === 'effectiveness'
                  ? 'bg-[#0284c7] text-white shadow-2xs'
                  : 'hover:text-[#1e293b]'
              }`}
            >
              Effectiveness %
            </button>
          </div>
        </div>
      </div>

      {/* Grid of Prioritized Teaching Method Cards */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
        {sortedMethods.map((method) => {
          const isTopRanked = method.priorityRank === 1;

          return (
            <div
              key={method.id}
              className={`group relative flex flex-col justify-between rounded-3xl border bg-white p-5 transition-all duration-200 hover:-translate-y-1 hover:shadow-lg ${
                isTopRanked
                  ? 'border-[#38bdf8] shadow-[0_4px_20px_rgba(2,132,199,0.08)] ring-1 ring-[#38bdf8]/40'
                  : 'border-[#e2e8f0] shadow-[0_2px_10px_rgba(0,0,0,0.02)] hover:border-[#cbd5e1]'
              }`}
            >
              {/* Top Badge & Priority Indicator */}
              <div>
                <div className="flex items-center justify-between">
                  <div
                    className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-extrabold"
                    style={{
                      backgroundColor: method.accentBg,
                      color: method.accentText,
                      border: `1px solid ${method.accentBorder}`,
                    }}
                  >
                    <span>#{method.priorityRank}</span>
                    <span>â€¢</span>
                    <span>{method.badgeLabel}</span>
                  </div>

                  {isTopRanked && (
                    <span className="flex items-center gap-1 text-[11px] font-bold text-[#0284c7]">
                      <svg className="h-3.5 w-3.5 fill-current" viewBox="0 0 24 24">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                      </svg>
                      Primary
                    </span>
                  )}
                </div>

                {/* Method Title & Tagline */}
                <div className="mt-4">
                  <h3 className="text-xl font-extrabold text-[#1e293b] group-hover:text-[#0284c7] transition-colors">
                    {method.name}
                  </h3>
                  <p className="mt-1 text-xs font-medium leading-relaxed text-[#64748b]">
                    {method.tagline}
                  </p>
                </div>

                {/* Effectiveness Metric Gauge */}
                <div className="mt-4 rounded-2xl bg-[#f8fafc] p-3 border border-[#f1f5f9]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#64748b]">Observed Success</span>
                    <span className="font-extrabold text-[#1e293b]">
                      {method.effectivenessPercent}%
                    </span>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#e2e8f0]">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.max(method.effectivenessPercent, 4)}%`,
                        backgroundColor: method.color,
                      }}
                    />
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-[#94a3b8]">
                    <span>Resolution Rate</span>
                    <span>{method.successfulUses} wins recorded</span>
                  </div>
                </div>

                {/* Pedagogical Focus & AI Trigger */}
                <div className="mt-4 space-y-2 text-xs">
                  <div>
                    <span className="font-bold text-[#475569] uppercase text-[10px] tracking-wider">
                      Pedagogical Focus
                    </span>
                    <p className="mt-0.5 text-[#334155] leading-relaxed">
                      {method.pedagogicalFocus}
                    </p>
                  </div>

                  <div>
                    <span className="font-bold text-[#475569] uppercase text-[10px] tracking-wider">
                      AI Trigger Logic
                    </span>
                    <p className="mt-0.5 text-[#64748b] leading-relaxed line-clamp-2">
                      {method.aiEscalationRule}
                    </p>
                  </div>
                </div>

                {/* Key Strengths */}
                <div className="mt-4 border-t border-[#f1f5f9] pt-3">
                  <span className="font-bold text-[#475569] uppercase text-[10px] tracking-wider">
                    Key Advantages
                  </span>
                  <ul className="mt-1.5 space-y-1 text-xs text-[#475569]">
                    {method.keyStrengths.slice(0, 2).map((strength, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-[#0284c7] font-bold">âœ“</span>
                        <span className="line-clamp-1">{strength}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-5 pt-3 border-t border-[#f1f5f9] flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSelectMethod(method)}
                  className="flex-1 rounded-xl border border-[#d7e4ed] bg-white py-2 text-xs font-bold text-[#1e293b] hover:bg-[#f8fafc] hover:border-[#cbd5e1] transition-colors"
                >
                  View Details
                </button>
                <button
                  type="button"
                  onClick={() => onTestStrategy(method.id)}
                  className="rounded-xl px-3 py-2 text-xs font-bold text-white transition-opacity hover:opacity-90"
                  style={{ backgroundColor: method.color }}
                  title={`Test ${method.name} strategy in AI Tutor`}
                >
                  Test Style
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

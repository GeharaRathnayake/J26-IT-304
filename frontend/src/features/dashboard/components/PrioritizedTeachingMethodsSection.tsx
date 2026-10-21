import React, { useState } from 'react';
import type { TeachingMethodCard, WeakTopicItem } from '../types';
import type { Strategy } from '../../tutor/api/types';

interface PrioritizedTeachingMethodsSectionProps {
  methods: TeachingMethodCard[];
  selectedTopicForPreview?: WeakTopicItem;
  allTopics: WeakTopicItem[];
  onSelectTopicForPreview: (topic: WeakTopicItem) => void;
  onOpenVoiceTutorWithStrategy: (strategy: Strategy) => void;
}

export const PrioritizedTeachingMethodsSection: React.FC<
  PrioritizedTeachingMethodsSectionProps
> = ({
  methods,
  selectedTopicForPreview,
  allTopics,
  onSelectTopicForPreview,
  onOpenVoiceTutorWithStrategy,
}) => {
  const [activeStrategyPreview, setActiveStrategyPreview] = useState<Strategy | null>('analogy');

  const currentTopic = selectedTopicForPreview || allTopics[0];

  return (
    <div
      id="teaching-methods"
      className="bg-white border border-[#dce8e5] rounded-3xl p-6 md:p-8 shadow-sm shadow-teal-900/5 space-y-6"
    >
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#edf4f2]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-xl md:text-2xl font-extrabold text-[#112e29] tracking-tight">
              Prioritized Personalized Teaching Method Cards
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-[#e6f7f3] text-[#0ca58e] border border-[#bfeade]">
              PP1 Pedagogical Engine
            </span>
          </div>
          <p className="text-sm text-[#4c726c] font-medium leading-relaxed max-w-3xl">
            Observed Strategy Effectiveness ranked for your cognitive learning profile. When you
            encounter confusion during tutoring, the escalation engine prioritizes these methods
            in sequence rather than repeating identical explanations.
          </p>
        </div>

        {/* Live Topic Context Selector */}
        <div className="flex items-center gap-2 bg-[#f4f9f7] px-3.5 py-2 rounded-2xl border border-[#d8e7e3]">
          <span className="text-xs font-bold text-[#557b75] whitespace-nowrap">Topic Context:</span>
          <select
            value={currentTopic?.id}
            onChange={(e) => {
              const found = allTopics.find((t) => t.id === e.target.value);
              if (found) onSelectTopicForPreview(found);
            }}
            className="text-xs font-bold text-[#113a33] bg-transparent focus:outline-none cursor-pointer"
          >
            {allTopics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Observed Strategy Effectiveness Summary (Upgraded from demo's 0% bars) */}
      <div className="bg-[#f8fbfb] border border-[#e2edea] rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h4 className="text-sm font-bold text-[#143d36] flex items-center gap-2">
              <span>Observed Strategy Effectiveness</span>
              <span className="text-[11px] font-normal text-[#5a807a]">
                (Share of successful explanations per strategy)
              </span>
            </h4>
            <p className="text-xs text-[#5f847e] mt-0.5">
              This measures real student breakthroughs when a strategy is applied during confusion.
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs font-bold text-[#456b64]">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
              <span>Analogy (88%)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
              <span>Example (76%)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span>Simplified (62%)</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span>Theory (38%)</span>
            </span>
          </div>
        </div>

        {/* Multi-segmented or clean stacked progress meters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {methods.map((method) => (
            <div
              key={method.strategy}
              onClick={() => setActiveStrategyPreview(method.strategy)}
              className={`p-3 rounded-xl border transition-all cursor-pointer ${
                activeStrategyPreview === method.strategy
                  ? 'bg-white border-[#0ca58e] shadow-sm ring-1 ring-[#0ca58e]/30'
                  : 'bg-white/80 border-[#e3edea] hover:bg-white'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-bold mb-1.5">
                <span className="text-[#1a443d]">{method.shortLabel}</span>
                <span
                  className={
                    method.successRate >= 80
                      ? 'text-emerald-700'
                      : method.successRate >= 70
                      ? 'text-sky-700'
                      : method.successRate >= 50
                      ? 'text-amber-700'
                      : 'text-purple-700'
                  }
                >
                  {method.successRate}%
                </span>
              </div>
              <div className="w-full bg-[#ecf4f2] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    method.strategy === 'analogy'
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-500'
                      : method.strategy === 'example'
                      ? 'bg-gradient-to-r from-sky-500 to-blue-500'
                      : method.strategy === 'simplified'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                      : 'bg-gradient-to-r from-purple-500 to-indigo-500'
                  }`}
                  style={{ width: `${method.successRate}%` }}
                />
              </div>
              <div className="flex justify-between items-center text-[10px] text-[#698e88] mt-1.5 font-medium">
                <span>{method.winCount} wins / {method.totalUses} uses</span>
                <span>Rank #{method.rank}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* The 4 Prioritized Method Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {methods.map((card) => {
          const isTop = card.isTopRecommendation;
          const isSelected = activeStrategyPreview === card.strategy;
          const sample = currentTopic?.explanationSamples?.[card.strategy];

          return (
            <div
              key={card.strategy}
              className={`rounded-3xl p-6 transition-all relative overflow-hidden flex flex-col justify-between border ${
                isTop
                  ? 'bg-gradient-to-b from-[#f3faf8] to-white border-[#0ca58e] shadow-md shadow-teal-900/5 ring-1 ring-[#0ca58e]/40'
                  : 'bg-white border-[#dce8e5] hover:border-[#0ca58e]/40 shadow-xs hover:shadow-md'
              }`}
            >
              {/* Top Accent Ribbon for #1 */}
              {isTop && (
                <div className="absolute top-0 right-0 bg-gradient-to-l from-[#0ca58e] to-[#0a8976] text-white text-[10px] font-black uppercase tracking-wider py-1 px-4 rounded-bl-xl shadow-xs">
                  â˜… TOP PERSONALIZED MATCH
                </div>
              )}

              <div>
                {/* Priority Rank & Method Title */}
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className={`w-9 h-9 rounded-2xl flex items-center justify-center font-black text-sm shrink-0 ${
                      card.strategy === 'analogy'
                        ? 'bg-emerald-500 text-white shadow-sm shadow-emerald-500/30'
                        : card.strategy === 'example'
                        ? 'bg-sky-500 text-white shadow-sm shadow-sky-500/30'
                        : card.strategy === 'simplified'
                        ? 'bg-amber-500 text-white shadow-sm shadow-amber-500/30'
                        : 'bg-purple-500 text-white shadow-sm shadow-purple-500/30'
                    }`}
                  >
                    #{card.rank}
                  </div>
                  <div>
                    <h4 className="text-lg font-extrabold text-[#11312c] tracking-tight leading-tight">
                      {card.name}
                    </h4>
                    <p className="text-xs text-[#527771] font-medium">{card.tagline}</p>
                  </div>
                </div>

                {/* Efficacy Stats Strip */}
                <div className="flex flex-wrap items-center gap-2 py-3 border-y border-[#edf4f2] my-3">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#f0f8f6] rounded-lg text-xs font-bold text-[#144b41]">
                    <span className="text-[#0ca58e]">ðŸŽ¯</span>
                    <span>{card.successRate}% Breakthrough Rate</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#f0f8f6] rounded-lg text-xs font-bold text-[#144b41]">
                    <span>â±ï¸</span>
                    <span>{card.avgResolutionTimeMinutes} min Avg Resolution</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#f0f8f6] rounded-lg text-xs font-bold text-[#144b41]">
                    <span>ðŸ†</span>
                    <span>{card.winCount} Wins</span>
                  </div>
                </div>

                {/* Cognitive Insight Box */}
                <div className="bg-[#f7faf9] rounded-2xl p-4 border border-[#e5eeec] mb-4">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-[#15463e] mb-1.5">
                    <span className="text-[#0ca58e]">ðŸ’¡</span>
                    <span>Why this works for your cognitive profile</span>
                  </div>
                  <p className="text-xs text-[#4b6f68] leading-relaxed font-medium">
                    {card.whyItWorks}
                  </p>
                  <div className="mt-2 text-[11px] font-bold text-[#0ca58e]">
                    âœ“ {card.cognitiveProfileMatch}
                  </div>
                </div>

                {/* Live Strategy Sample Dropdown / Preview Accordion */}
                <div className="mb-4">
                  <button
                    type="button"
                    onClick={() =>
                      setActiveStrategyPreview(isSelected ? null : card.strategy)
                    }
                    className="w-full flex items-center justify-between px-3.5 py-2.5 bg-[#f2f8f6] hover:bg-[#e6f4f1] text-[#14483f] rounded-xl text-xs font-bold transition-all border border-[#d4e6e2]"
                  >
                    <span className="flex items-center gap-2">
                      <span>ðŸ‘ï¸</span>
                      <span>
                        Explanation Preview: <span className="underline">{currentTopic?.title}</span>
                      </span>
                    </span>
                    <svg
                      className={`w-4 h-4 transition-transform ${isSelected ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Expanded Sample Content */}
                  {isSelected && sample && (
                    <div className="mt-2.5 p-4 bg-white border border-[#cbe4de] rounded-2xl shadow-inner text-xs space-y-2.5 animate-fadeIn">
                      <div className="flex items-center justify-between border-b border-[#edf4f2] pb-1.5">
                        <span className="font-bold text-[#133c35]">{sample.title}</span>
                        <span className="text-[10px] text-[#638c85] font-semibold">{sample.subtitle}</span>
                      </div>
                      <p className="text-[#3c615a] leading-relaxed font-medium whitespace-pre-line">
                        {sample.content}
                      </p>
                      {sample.codeSnippet && (
                        <div className="mt-2">
                          <div className="text-[10px] font-bold text-[#567a74] mb-1">Code demonstration:</div>
                          <pre className="p-3 bg-[#112320] text-[#a7f3d0] rounded-xl text-[11px] font-mono overflow-x-auto leading-relaxed border border-[#21433d]">
                            {sample.codeSnippet}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="flex items-center justify-between gap-3 pt-3 border-t border-[#edf4f2]">
                <span className="text-[11px] text-[#638983] font-semibold">
                  Escalation Tier: Priority #{card.rank}
                </span>

                <button
                  type="button"
                  onClick={() => onOpenVoiceTutorWithStrategy(card.strategy)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs ${
                    isTop
                      ? 'bg-gradient-to-r from-[#0ca58e] to-[#078572] hover:from-[#0dae96] hover:to-[#099580] text-white hover:scale-[1.02]'
                      : 'bg-[#eef6f4] hover:bg-[#dfeeed] text-[#14473e] hover:text-[#0b6b5d]'
                  }`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                    />
                  </svg>
                  <span>Practice with {card.shortLabel}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

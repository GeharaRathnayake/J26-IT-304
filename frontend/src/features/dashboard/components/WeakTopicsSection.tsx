import React, { useState, useMemo } from 'react';
import type { WeakTopicItem, Severity } from '../types';

interface WeakTopicsSectionProps {
  weakTopics: WeakTopicItem[];
  onOpenVoiceTutorWithTopic: (slug: string) => void;
  onInspectTopic: (topic: WeakTopicItem) => void;
  onResolveTopic: (id: string) => void;
  onOpenQuizModal?: (topic: WeakTopicItem) => void;
}

export const WeakTopicsSection: React.FC<WeakTopicsSectionProps> = ({
  weakTopics,
  onOpenVoiceTutorWithTopic,
  onInspectTopic,
  onResolveTopic,
  onOpenQuizModal,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTopics = useMemo(() => {
    return weakTopics.filter((topic) => {
      const matchesSeverity =
        filterSeverity === 'all' || topic.severity === filterSeverity;
      const matchesSearch =
        topic.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        topic.cognitiveBlocker.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSeverity && matchesSearch;
    });
  }, [weakTopics, filterSeverity, searchQuery]);

  return (
    <div
      id="weakness-topics"
      className="bg-white border border-[#dce8e5] rounded-3xl p-6 md:p-8 shadow-sm shadow-teal-900/5"
    >
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#edf4f2]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-xl md:text-2xl font-extrabold text-[#112e29] tracking-tight">
              Weakness topic area
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-rose-50 text-rose-600 border border-rose-200">
              {weakTopics.length} Flagged
            </span>
          </div>
          <p className="text-sm text-[#4c726c] font-medium leading-relaxed max-w-2xl">
            A topic is stored here as <span className="font-bold text-rose-600">WEAK</span> when the
            student needed 3 strategies to understand that one question. The adaptive engine
            logs these to prioritize personalized remedial learning.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search weak topics..."
            className="w-full pl-9 pr-4 py-2 bg-[#f4f9f7] hover:bg-[#edf5f3] focus:bg-white text-xs font-semibold text-[#143d36] rounded-xl border border-[#d4e4e0] focus:border-[#0ca58e] focus:outline-none transition-all placeholder:text-[#7f9f99]"
          />
          <svg
            className="w-4 h-4 text-[#7f9f99] absolute left-3 top-2.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 pt-4 pb-6">
        <span className="text-xs font-bold text-[#628781] mr-1">Filter by Severity:</span>
        <button
          type="button"
          onClick={() => setFilterSeverity('all')}
          className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
            filterSeverity === 'all'
              ? 'bg-[#124b42] text-white shadow-xs'
              : 'bg-[#f0f7f5] text-[#426c65] hover:bg-[#e4f2ee]'
          }`}
        >
          All ({weakTopics.length})
        </button>
        <button
          type="button"
          onClick={() => setFilterSeverity('critical')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
            filterSeverity === 'critical'
              ? 'bg-rose-600 text-white shadow-xs'
              : 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
          <span>Critical (3+ Strategies)</span>
        </button>
        <button
          type="button"
          onClick={() => setFilterSeverity('moderate')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
            filterSeverity === 'moderate'
              ? 'bg-amber-600 text-white shadow-xs'
              : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <span>Moderate (2 Cycles)</span>
        </button>
      </div>

      {/* Topic Cards List */}
      <div className="space-y-4">
        {filteredTopics.length === 0 ? (
          <div className="p-8 text-center bg-[#f9fcfa] rounded-2xl border border-dashed border-[#cfe0db]">
            <p className="text-sm font-semibold text-[#547973]">
              No weak topics match the selected filter.
            </p>
          </div>
        ) : (
          filteredTopics.map((topic) => (
            <div
              key={topic.id}
              className="bg-[#fafdfc] hover:bg-white border border-[#dce8e5] hover:border-[#0ca58e]/40 rounded-2xl p-5 transition-all shadow-xs hover:shadow-md hover:shadow-teal-900/5 group"
            >
              {/* Card Header Row */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-[#edf4f2]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#e4f6f2] to-[#d3ede7] text-[#0ca58e] flex items-center justify-center font-black text-base shadow-xs">
                    {topic.title.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-base font-bold text-[#14342e] tracking-tight">
                        {topic.title}
                      </h4>
                      {/* Exact WEAK tag from screenshot elevated */}
                      <span className="px-2 py-0.5 rounded-md text-[11px] font-black uppercase tracking-wider bg-rose-100 text-rose-700 border border-rose-300">
                        WEAK
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-[#5f857f] font-medium mt-0.5">
                      <span>{topic.category}</span>
                      <span>â€¢</span>
                      <span>Needed {topic.cyclesNeeded} strategies</span>
                      <span>â€¢</span>
                      <span>Last: {topic.lastEncountered}</span>
                    </div>
                  </div>
                </div>

                {/* Mastery Bar */}
                <div className="flex items-center gap-3 min-w-[160px]">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs font-semibold text-[#577974] mb-1">
                      <span>Mastery</span>
                      <span className="font-bold text-[#184841]">{topic.masteryScore}%</span>
                    </div>
                    <div className="w-full bg-[#e7f0ee] h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          topic.masteryScore < 40
                            ? 'bg-rose-500'
                            : topic.masteryScore < 60
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${topic.masteryScore}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Cognitive Blocker & Misconception */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                <div className="bg-[#f2f8f6] rounded-xl p-3 border border-[#ddeae7]">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-[#1b4e45] mb-1">
                    <span className="text-[#0ca58e]">ðŸ§ </span>
                    <span>Detected Misconception</span>
                  </div>
                  <p className="text-xs text-[#4b6f68] leading-relaxed font-medium">
                    {topic.detectedMisconception}
                  </p>
                </div>

                <div className="bg-[#fff9f6] rounded-xl p-3 border border-[#fae5d9]">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 mb-1">
                    <span>âš ï¸</span>
                    <span>Frequent Error Trigger</span>
                  </div>
                  <p className="text-xs font-mono text-amber-800 bg-white/80 px-2 py-1 rounded border border-amber-200 inline-block">
                    {topic.commonCompilerOrLogicError}
                  </p>
                </div>
              </div>

              {/* Strategy Escalation Journey */}
              <div className="bg-white rounded-xl p-3.5 border border-[#e1ece9] mb-4">
                <div className="flex items-center justify-between text-xs font-bold text-[#456b64] mb-2.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#0ca58e]" />
                    <span>Observed Strategy Escalation Sequence</span>
                  </span>
                  <span className="text-[11px] text-[#0ca58e] font-semibold bg-[#e7f7f4] px-2 py-0.5 rounded-md">
                    Breakthrough on: {topic.recommendedMethod.toUpperCase()}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {topic.strategiesAttempted.map((step, idx) => (
                    <React.Fragment key={idx}>
                      <div
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border ${
                          step.outcome === 'breakthrough'
                            ? 'bg-emerald-50 border-emerald-300 text-emerald-800 font-bold shadow-xs'
                            : 'bg-rose-50/70 border-rose-200 text-rose-700'
                        }`}
                      >
                        <span>{step.outcome === 'breakthrough' ? 'âœ…' : 'âŒ'}</span>
                        <span>{step.strategyLabel}</span>
                        <span className="text-[10px] opacity-75">
                          {step.outcome === 'breakthrough' ? '(Understood)' : '(Confused)'}
                        </span>
                      </div>
                      {idx < topic.strategiesAttempted.length - 1 && (
                        <svg
                          className="w-3.5 h-3.5 text-[#9ab7b1]"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Card Action Buttons */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onOpenVoiceTutorWithTopic(topic.slug)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-[#0ca58e] to-[#08826f] hover:from-[#0dae96] hover:to-[#0a907b] text-white text-xs font-bold rounded-xl shadow-xs transition-all hover:scale-[1.02] active:scale-[0.98]"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                      />
                    </svg>
                    <span>Practice with Voice Tutor</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onInspectTopic(topic)}
                    className="flex items-center gap-1.5 px-3 py-2 bg-[#f0f8f6] hover:bg-[#e2f3ee] text-[#14473e] text-xs font-bold rounded-xl border border-[#c6e4dd] transition-all"
                  >
                    <svg className="w-3.5 h-3.5 text-[#0ca58e]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                    <span>Inspect Diagnostic Transcript</span>
                  </button>

                  {onOpenQuizModal && (
                    <button
                      type="button"
                      onClick={() => onOpenQuizModal(topic)}
                      className="flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-[#f6fbf9] text-[#2b5a51] text-xs font-bold rounded-xl border border-[#d6e7e3] transition-all"
                    >
                      <svg className="w-3.5 h-3.5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Checkup Quiz</span>
                    </button>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => onResolveTopic(topic.id)}
                  className="text-xs font-semibold text-[#668b84] hover:text-emerald-700 hover:underline py-1"
                >
                  Mark as Resolved âœ“
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

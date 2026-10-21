import { useState } from 'react';
import type { WeakTopicItem } from '../types';

interface WeaknessTopicAreaProps {
  weakTopics: WeakTopicItem[];
  onSelectTopic: (topic: WeakTopicItem) => void;
  onPracticeTopic: (topicId: string) => void;
}

export function WeaknessTopicArea({
  weakTopics,
  onSelectTopic,
  onPracticeTopic,
}: WeaknessTopicAreaProps) {
  const [filter, setFilter] = useState<'ALL' | 'WEAK'>('ALL');

  const filteredTopics = filter === 'ALL'
    ? weakTopics
    : weakTopics.filter((t) => t.severity === 'WEAK');

  return (
    <div className="flex flex-col rounded-3xl border border-[#e2e8f0] bg-white p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)] transition-all">
      {/* Header section matching uploaded image */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-extrabold text-[#1e293b]">
            Weakness topic area
          </h2>
          {weakTopics.length > 1 && (
            <div className="flex items-center gap-1 rounded-lg bg-[#f1f5f9] p-0.5 text-xs font-semibold text-[#64748b]">
              <button
                type="button"
                onClick={() => setFilter('ALL')}
                className={`rounded px-2 py-0.5 ${
                  filter === 'ALL' ? 'bg-white text-[#1e293b] shadow-xs' : ''
                }`}
              >
                All ({weakTopics.length})
              </button>
              <button
                type="button"
                onClick={() => setFilter('WEAK')}
                className={`rounded px-2 py-0.5 ${
                  filter === 'WEAK' ? 'bg-white text-[#ef4444] shadow-xs' : ''
                }`}
              >
                Only Weak
              </button>
            </div>
          )}
        </div>
        <p className="mt-1 text-sm leading-relaxed text-[#64748b]">
          A topic is stored here as WEAK when the student needed 3 strategies to understand that one question.
        </p>
      </div>

      {/* Divider matching screenshot */}
      <hr className="my-5 border-t border-[#f1f5f9]" />

      {/* Weak Topic Items List */}
      <div className="space-y-3">
        {filteredTopics.length === 0 ? (
          <div className="py-8 text-center text-sm text-[#94a3b8]">
            No weak topics recorded yet.
          </div>
        ) : (
          filteredTopics.map((topic) => (
            <div
              key={topic.id}
              className="group flex flex-col justify-between rounded-xl border border-transparent p-3 transition-all hover:border-[#fecdd3] hover:bg-[#fff1f2]/30 sm:flex-row sm:items-center"
            >
              <div
                className="cursor-pointer"
                onClick={() => onSelectTopic(topic)}
              >
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold text-[#1e293b] group-hover:text-[#e11d48] transition-colors">
                    {topic.name}
                  </span>
                  <span className="text-xs text-[#94a3b8]">
                    ({topic.strategiesNeeded} strategies used)
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[#64748b]">
                  <span className="inline-flex items-center gap-1 text-[#0284c7]">
                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                    {topic.lastEncountered}
                  </span>
                  <span>â€¢</span>
                  <span>{topic.subtopics[0] || 'Core concepts'}</span>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-3 sm:mt-0">
                <button
                  type="button"
                  onClick={() => onPracticeTopic(topic.id)}
                  className="hidden rounded-lg border border-[#e2e8f0] bg-white px-2.5 py-1 text-xs font-semibold text-[#0369a1] shadow-2xs hover:bg-[#f0f9ff] hover:border-[#bae6fd] group-hover:inline-flex"
                >
                  Practice in Tutor
                </button>
                <button
                  type="button"
                  onClick={() => onSelectTopic(topic)}
                  className="cursor-pointer font-extrabold tracking-wider text-[#ef4444] hover:opacity-80 uppercase text-xs"
                >
                  {topic.severity}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer rule audit explanation */}
      <div className="mt-6 flex items-center justify-between rounded-2xl bg-[#f8fafc] p-3 text-xs text-[#64748b]">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-[#0284c7]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>
            Audit Rule: <code className="rounded bg-[#e2e8f0] px-1 py-0.5 text-[11px] font-mono text-[#0f172a]">counted_strategies &gt;= 3 || outcome == end_unresolved</code>
          </span>
        </div>
        <span className="font-semibold text-[#0284c7] hover:underline cursor-pointer" onClick={() => onSelectTopic(weakTopics[0])}>
          Inspect Breakdown &rarr;
        </span>
      </div>
    </div>
  );
}

import type { TeachingMethod, WeakTopicItem } from '../types';

interface TopicDetailsModalProps {
  topic: WeakTopicItem | null;
  method: TeachingMethod | null;
  onClose: () => void;
  onPracticeTopic: (topicId: string) => void;
}

export function TopicDetailsModal({
  topic,
  method,
  onClose,
  onPracticeTopic,
}: TopicDetailsModalProps) {
  if (!topic && !method) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f172a]/40 p-4 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl transition-all sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-5 top-5 flex h-8 w-8 items-center justify-center rounded-full bg-[#f1f5f9] text-[#64748b] hover:bg-[#e2e8f0] hover:text-[#0f172a]"
          aria-label="Close modal"
        >
          âœ•
        </button>

        {topic && (
          <div>
            {/* Header */}
            <div className="flex items-center gap-3">
              <span className="rounded-full bg-[#fee2e2] px-3 py-1 text-xs font-black tracking-wider text-[#b91c1c] uppercase">
                {topic.severity}
              </span>
              <span className="text-xs font-bold text-[#64748b]">
                {topic.strategiesNeeded} Strategies Escalated
              </span>
            </div>

            <h2 className="mt-3 text-2xl font-black text-[#1e293b]">
              {topic.name}
            </h2>

            <p className="mt-2 text-sm leading-relaxed text-[#475569]">
              {topic.ruleExplanation}
            </p>

            {/* Threshold Rule Audit Callout */}
            <div className="mt-5 rounded-2xl border border-[#fecdd3] bg-[#fff1f2] p-4 text-xs">
              <div className="flex items-center gap-2 font-bold text-[#9f1239]">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 9v4M12 17h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                <span>Weakness Detection Mechanism (Claim C6 & Invariant I1)</span>
              </div>
              <p className="mt-1 text-[#881337] leading-relaxed">
                When a student encounters conceptual confusion, the AI tutor sequentially tries up to 3 non-requested strategies. If 3 strategies are needed without resolution or the episode ends unresolved, the topic is automatically logged to the weakness record.
              </p>
            </div>

            {/* Escalation Sequence Breakdown */}
            <div className="mt-6">
              <h3 className="text-xs font-extrabold tracking-wider text-[#64748b] uppercase">
                Observed Tutoring Escalation Trace
              </h3>
              <div className="mt-3 space-y-2.5">
                {topic.cycleHistory.map((step) => (
                  <div
                    key={step.cycle}
                    className="flex items-center justify-between rounded-xl border border-[#e2e8f0] bg-[#f8fafc] p-3 text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#e2e8f0] font-bold text-[#334155]">
                        {step.cycle}
                      </span>
                      <span className="font-bold text-[#1e293b] uppercase">
                        Strategy: {step.strategy}
                      </span>
                    </div>
                    <span
                      className={`rounded-md px-2 py-0.5 font-bold uppercase text-[10px] ${
                        step.result === 'confused'
                          ? 'bg-[#fee2e2] text-[#991b1b]'
                          : 'bg-[#dcfce7] text-[#166534]'
                      }`}
                    >
                      Student Result: {step.result}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Subtopics and Trouble spots */}
            <div className="mt-6">
              <h3 className="text-xs font-extrabold tracking-wider text-[#64748b] uppercase">
                Stumbling Blocks Identified
              </h3>
              <ul className="mt-2 space-y-1.5 text-xs text-[#334155]">
                {topic.confusionTriggers.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#ef4444]">â€¢</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Next Recommended Step */}
            <div className="mt-6 rounded-2xl bg-[#f0f9ff] p-4 border border-[#bae6fd]">
              <span className="text-xs font-bold text-[#0369a1] uppercase tracking-wide">
                Recommended Remediation
              </span>
              <p className="mt-1 text-xs text-[#0c4a6e] font-medium leading-relaxed">
                {topic.suggestedAction}
              </p>
            </div>

            {/* Modal Actions */}
            <div className="mt-8 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-[#cbd5e1] px-4 py-2 text-xs font-bold text-[#475569] hover:bg-[#f1f5f9]"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onPracticeTopic(topic.id);
                }}
                className="rounded-xl bg-[#0284c7] px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-[#0369a1]"
              >
                Launch Voice Tutor for &ldquo;{topic.name}&rdquo;
              </button>
            </div>
          </div>
        )}

        {method && !topic && (
          <div>
            <div className="flex items-center gap-2">
              <span
                className="rounded-full px-3 py-1 text-xs font-black uppercase"
                style={{
                  backgroundColor: method.accentBg,
                  color: method.accentText,
                  border: `1px solid ${method.accentBorder}`,
                }}
              >
                Rank #{method.priorityRank} Â· {method.badgeLabel}
              </span>
              <span className="text-xs font-bold text-[#64748b]">
                {method.effectivenessPercent}% Success Share
              </span>
            </div>

            <h2 className="mt-3 text-2xl font-black text-[#1e293b]">
              {method.name} Strategy
            </h2>

            <p className="mt-1 text-sm text-[#0284c7] font-semibold">
              {method.tagline}
            </p>

            <p className="mt-3 text-sm leading-relaxed text-[#475569]">
              {method.description}
            </p>

            {/* Pedagogical Framework */}
            <div className="mt-6 rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-4 text-xs space-y-3">
              <div>
                <span className="font-extrabold text-[#1e293b] uppercase tracking-wider text-[11px]">
                  Pedagogical Target
                </span>
                <p className="mt-1 text-[#475569]">{method.pedagogicalFocus}</p>
              </div>

              <div>
                <span className="font-extrabold text-[#1e293b] uppercase tracking-wider text-[11px]">
                  AI Escalation Trigger
                </span>
                <p className="mt-1 text-[#475569]">{method.aiEscalationRule}</p>
              </div>

              <div>
                <span className="font-extrabold text-[#1e293b] uppercase tracking-wider text-[11px]">
                  Typical Prompt Example
                </span>
                <p className="mt-1 font-mono text-[11px] text-[#0369a1] bg-white p-2 rounded-lg border border-[#e2e8f0]">
                  &ldquo;{method.sampleTrigger}&rdquo;
                </p>
              </div>
            </div>

            {/* Key Advantages */}
            <div className="mt-6">
              <h3 className="text-xs font-extrabold tracking-wider text-[#64748b] uppercase">
                Learner Advantages
              </h3>
              <ul className="mt-2 space-y-1.5 text-xs text-[#334155]">
                {method.keyStrengths.map((strength, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#0284c7] font-bold">âœ“</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Modal Actions */}
            <div className="mt-8 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-[#cbd5e1] px-4 py-2 text-xs font-bold text-[#475569] hover:bg-[#f1f5f9]"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onPracticeTopic(method.id);
                }}
                className="rounded-xl bg-[#0284c7] px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-[#0369a1]"
              >
                Test this strategy in Tutor
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

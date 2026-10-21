import React, { useState } from 'react';
import type { WeakTopicItem } from '../types';

interface TopicDiagnosticModalProps {
  topic: WeakTopicItem | null;
  onClose: () => void;
  onLaunchVoiceTutor: (slug: string) => void;
}

export const TopicDiagnosticModal: React.FC<TopicDiagnosticModalProps> = ({
  topic,
  onClose,
  onLaunchVoiceTutor,
}) => {
  const [selectedQuizAnswer, setSelectedQuizAnswer] = useState<number | null>(null);
  const [showQuizResult, setShowQuizResult] = useState(false);

  if (!topic) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-3xl border border-[#d6e7e3] shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-[#edf4f2] flex items-center justify-between bg-[#f8fbfb]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-rose-500 to-rose-600 text-white flex items-center justify-center font-bold text-sm shadow-sm shadow-rose-500/20">
              âš ï¸
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-extrabold text-[#11312b]">{topic.title}</h3>
                <span className="px-2 py-0.5 rounded text-[11px] font-extrabold bg-rose-100 text-rose-700">
                  WEAKNESS LOG
                </span>
              </div>
              <p className="text-xs text-[#567a74] font-medium">
                {topic.category} â€¢ Required {topic.cyclesNeeded} strategies to resolve
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-[#edf5f3] hover:bg-[#dfeeed] text-[#345b54] flex items-center justify-center font-bold transition-colors"
          >
            âœ•
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Cognitive Diagnosis Callout */}
          <div className="bg-[#f0f8f6] border border-[#cfe6e0] rounded-2xl p-4">
            <h4 className="text-xs font-bold text-[#14473e] uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <span>ðŸ§ </span>
              <span>Cognitive Diagnosis</span>
            </h4>
            <p className="text-xs text-[#375e57] leading-relaxed font-medium">
              {topic.cognitiveBlocker}
            </p>
          </div>

          {/* Turn-by-Turn Escalation Transcript */}
          <div>
            <h4 className="text-xs font-extrabold text-[#11332d] uppercase tracking-wider mb-3 flex items-center gap-2">
              <span>Observed Tutoring Episode Dialogue</span>
              <span className="text-[10px] font-semibold text-[#0ca58e] bg-[#e6f7f3] px-2 py-0.5 rounded-full">
                Audit Trail (FR-16)
              </span>
            </h4>
            <div className="space-y-3">
              {topic.strategiesAttempted.map((turn, i) => (
                <div
                  key={i}
                  className={`p-3.5 rounded-2xl border text-xs ${
                    turn.outcome === 'breakthrough'
                      ? 'bg-emerald-50/80 border-emerald-300 ring-1 ring-emerald-400/20'
                      : 'bg-[#fafcfb] border-[#e1edea]'
                  }`}
                >
                  <div className="flex items-center justify-between font-bold mb-1.5">
                    <span className="flex items-center gap-1.5">
                      <span>{turn.outcome === 'breakthrough' ? 'âœ…' : 'âŒ'}</span>
                      <span className="text-[#154139]">{turn.strategyLabel} Strategy</span>
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                        turn.outcome === 'breakthrough'
                          ? 'bg-emerald-200 text-emerald-900'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {turn.outcome === 'breakthrough' ? 'Breakthrough (Understood)' : 'Confused'}
                    </span>
                  </div>

                  <div className="text-[#3c615a] mb-2 leading-relaxed bg-white/70 p-2.5 rounded-xl border border-[#e8f1ef]">
                    <span className="font-bold text-[#14473e]">Tutor: </span>
                    {turn.tutorExcerpt}
                  </div>

                  <div className="text-[#557b75] italic pl-2 border-l-2 border-[#b8ded6]">
                    <span className="font-semibold text-[#25524a]">Student: </span>
                    {turn.studentResponse}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Checkup Quiz */}
          <div className="bg-[#fcfdfd] border border-[#dce9e6] rounded-2xl p-4">
            <h4 className="text-xs font-extrabold text-[#143d36] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span>ðŸ“</span>
              <span>1-Minute Concept Checkup Quiz</span>
            </h4>
            <p className="text-xs font-bold text-[#234d45] mb-3">
              {topic.practiceQuestion.question}
            </p>

            <div className="space-y-2">
              {topic.practiceQuestion.options.map((option, idx) => {
                const isSelected = selectedQuizAnswer === idx;
                const isCorrect = idx === topic.practiceQuestion.correctIndex;

                let optionClass =
                  'bg-white border-[#d8e7e3] text-[#345b54] hover:bg-[#f2f8f6]';
                if (showQuizResult) {
                  if (isCorrect) {
                    optionClass = 'bg-emerald-100 border-emerald-400 text-emerald-900 font-bold';
                  } else if (isSelected) {
                    optionClass = 'bg-rose-100 border-rose-300 text-rose-900';
                  }
                } else if (isSelected) {
                  optionClass = 'bg-[#e6f7f3] border-[#0ca58e] text-[#0ca58e] font-bold';
                }

                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setSelectedQuizAnswer(idx);
                      setShowQuizResult(true);
                    }}
                    className={`w-full text-left p-2.5 rounded-xl border text-xs transition-all ${optionClass}`}
                  >
                    <span className="font-bold mr-2">{String.fromCharCode(65 + idx)}.</span>
                    <span>{option}</span>
                  </button>
                );
              })}
            </div>

            {showQuizResult && (
              <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900">
                <span className="font-bold">Explanation: </span>
                {topic.practiceQuestion.explanation}
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-[#f8fbfb] border-t border-[#edf4f2] flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-white hover:bg-[#edf5f3] text-[#335952] text-xs font-bold rounded-xl border border-[#d2e3df] transition-all"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              onClose();
              onLaunchVoiceTutor(topic.slug);
            }}
            className="px-5 py-2.5 bg-gradient-to-r from-[#0ca58e] to-[#08826f] hover:from-[#0dae96] hover:to-[#0a907b] text-white text-xs font-bold rounded-xl shadow-xs transition-all hover:scale-[1.02]"
          >
            Launch Voice Tutor with this Topic ðŸŽ™ï¸
          </button>
        </div>
      </div>
    </div>
  );
};

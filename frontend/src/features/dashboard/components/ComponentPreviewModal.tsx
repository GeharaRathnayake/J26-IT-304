import React from 'react';
import type { NavItemKey } from './Sidebar';

interface ComponentPreviewModalProps {
  navItem: NavItemKey | null;
  onClose: () => void;
  onOpenVoiceTutor: () => void;
}

export const ComponentPreviewModal: React.FC<ComponentPreviewModalProps> = ({
  navItem,
  onClose,
  onOpenVoiceTutor,
}) => {
  if (!navItem || navItem === 'dashboard' || navItem === 'voice_tutor') return null;

  const componentDetails: Record<
    Exclude<NavItemKey, 'dashboard' | 'voice_tutor'>,
    {
      title: string;
      number: string;
      subtitle: string;
      icon: string;
      description: string;
      features: string[];
      linkToVoice: boolean;
    }
  > = {
    ide_tutor: {
      title: 'Java IDE Tutor',
      number: '1st component',
      subtitle: 'Code-Level Real-Time Error Correction & Hints',
      icon: 'ðŸ’»',
      description:
        'The Java IDE Tutor component embeds directly inside the programming editor to capture compiler diagnostics, stack traces, and logic defects as the student types.',
      features: [
        'Real-time compiler linting & syntax hints',
        'Scaffolded code completions for tricky OOP templates',
        'Pushes frequent compile errors directly to this Student Dashboard to tag weak areas',
      ],
      linkToVoice: true,
    },
    adaptive_quiz: {
      title: 'Adaptive Quiz',
      number: '3rd component',
      subtitle: 'Dynamic Difficulty Adjustment based on Mastery',
      icon: 'ðŸ“',
      description:
        'The Adaptive Quiz component evaluates conceptual retention using Item Response Theory (IRT) and dynamic MCQ difficulty scaling.',
      features: [
        'Dynamically generates questions targeting flagged weak topic areas',
        'Verifies whether breakthroughs with Analogies convert to long-term memory',
        'Feeds mastery scores back into the student profile',
      ],
      linkToVoice: true,
    },
    video_learning: {
      title: 'Smart Video Learning',
      number: '4th component',
      subtitle: 'Attention Tracking & Adaptive Video MCQs',
      icon: 'ðŸŽ¥',
      description:
        'The Smart Video Learning component synchronizes lecture video timestamps with adaptive quizzes and webcam attention estimation.',
      features: [
        'Pauses video during detected low-attention intervals',
        'Serves micro-assessments aligned with voice tutor weak topics',
        'Correlates video replay counts with conceptual difficulties',
      ],
      linkToVoice: false,
    },
  };

  const info = componentDetails[navItem];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-3xl border border-[#d6e7e3] shadow-2xl max-w-lg w-full p-6 md:p-8 space-y-5">
        <div className="flex items-center justify-between border-b border-[#edf4f2] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-[#e6f7f3] text-2xl flex items-center justify-center">
              {info.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-extrabold text-[#11312b]">{info.title}</h3>
                <span className="text-[11px] font-bold text-[#0ca58e] bg-[#e6f7f3] px-2 py-0.5 rounded-full">
                  {info.number}
                </span>
              </div>
              <p className="text-xs text-[#527771] font-medium">{info.subtitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-[#edf5f3] hover:bg-[#dfeeed] text-[#345b54] flex items-center justify-center font-bold"
          >
            âœ•
          </button>
        </div>

        <p className="text-xs text-[#4b6f68] leading-relaxed font-medium">
          {info.description}
        </p>

        <div className="bg-[#f7fbf9] p-4 rounded-2xl border border-[#e2eee9] space-y-2">
          <div className="text-xs font-bold text-[#15463e]">Key Research Capabilities:</div>
          <ul className="space-y-1.5 text-xs text-[#39615a]">
            {info.features.map((feat, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-[#0ca58e] font-bold">âœ“</span>
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-white text-[#345b54] text-xs font-bold rounded-xl border border-[#d2e3df] hover:bg-[#f0f7f5]"
          >
            Close
          </button>

          <button
            type="button"
            onClick={() => {
              onClose();
              onOpenVoiceTutor();
            }}
            className="px-5 py-2.5 bg-gradient-to-r from-[#0ca58e] to-[#078572] hover:from-[#0dae96] hover:to-[#099580] text-white text-xs font-bold rounded-xl shadow-xs transition-all hover:scale-[1.02]"
          >
            Switch to Java Voice Tutor (PP1) ðŸŽ™ï¸
          </button>
        </div>
      </div>
    </div>
  );
};

import React from 'react';

interface WelcomeHeroProps {
  studentName?: string;
  onOpenVoiceTutor: () => void;
  onResumeTopic?: (slug: string) => void;
}

export const WelcomeHero: React.FC<WelcomeHeroProps> = ({
  studentName = 'Demo',
  onOpenVoiceTutor,
  onResumeTopic,
}) => {
  return (
    <section className="bg-white border border-[#dce9e6] rounded-3xl p-6 md:p-8 shadow-sm shadow-teal-900/5 relative overflow-hidden">
      {/* Decorative gradient glow in background */}
      <div className="absolute -right-16 -top-16 w-80 h-80 bg-gradient-to-br from-[#cff3ec] to-[#99e2d3] rounded-full blur-3xl opacity-40 pointer-events-none" />
      <div className="absolute right-32 -bottom-20 w-64 h-64 bg-gradient-to-tr from-[#bee9f5] to-[#c7efe8] rounded-full blur-3xl opacity-30 pointer-events-none" />

      <div className="relative z-1 max-w-3xl">
        {/* Subtitle */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-extrabold tracking-widest text-[#5c857e] uppercase">
            STUDENT DASHBOARD
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-[#0ca58e]" />
          <span className="text-xs font-semibold text-[#0c7f6e] bg-[#e6f7f3] px-2 py-0.5 rounded-full border border-[#bfeade]">
            Adaptive AI Voice Tutor (J26-IT-304)
          </span>
        </div>

        {/* Main Heading */}
        <h2 className="text-3xl md:text-4xl font-extrabold text-[#112e29] tracking-tight mb-2">
          Welcome, {studentName}
        </h2>

        {/* Description */}
        <p className="text-base text-[#466963] leading-relaxed mb-6 font-medium">
          Start with Java Voice Tutor. Topic progress and cognitive strategy adaptation will appear on
          this dashboard. When you encounter tricky concepts, the tutor dynamically escalates through
          personalized teaching methods to match your learning style.
        </p>

        {/* Primary CTA and Quick Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onOpenVoiceTutor}
            className="group flex items-center gap-2.5 px-6 py-3.5 bg-gradient-to-r from-[#0ca58e] to-[#078572] hover:from-[#0dae96] hover:to-[#099580] text-white font-bold rounded-2xl shadow-lg shadow-teal-600/25 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <div className="w-6 h-6 rounded-lg bg-white/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                />
              </svg>
            </div>
            <span>Open Java Voice Tutor</span>
            <svg
              className="w-4 h-4 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>

          {onResumeTopic && (
            <button
              type="button"
              onClick={() => onResumeTopic('classes_and_objects')}
              className="flex items-center gap-2 px-4 py-3 bg-[#f2f8f6] hover:bg-[#e4f3ef] text-[#1b4e45] font-semibold text-sm rounded-2xl border border-[#cbe4df] transition-all"
            >
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              <span>Resume Weak Topic: Object & Class</span>
            </button>
          )}
        </div>

        {/* Feature Highlights Pills */}
        <div className="mt-6 pt-5 border-t border-[#edf4f2] flex flex-wrap items-center gap-4 text-xs font-semibold text-[#547973]">
          <div className="flex items-center gap-1.5">
            <span className="text-[#0ca58e]">âœ“</span>
            <span>Real-time Confusion Detection (TF-IDF + Rules)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#0ca58e]">âœ“</span>
            <span>4-Tier Strategy Escalation (Theory âž” Example âž” Simpler âž” Analogy)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[#0ca58e]">âœ“</span>
            <span>Zero Student Telemetry Leaked (100% Local Ollama LLM)</span>
          </div>
        </div>
      </div>
    </section>
  );
};

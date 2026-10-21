import type { TeachingMethod } from '../types';

interface StrategyEffectivenessProps {
  methods: TeachingMethod[];
  onSelectMethod: (method: TeachingMethod) => void;
}

export function StrategyEffectiveness({
  methods,
  onSelectMethod,
}: StrategyEffectivenessProps) {
  return (
    <div className="flex flex-col rounded-3xl border border-[#e2e8f0] bg-white p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)] transition-all">
      {/* Title & Subtext matching uploaded image */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-extrabold text-[#1e293b]">
            Observed Strategy Effectiveness
          </h2>
          <span className="rounded-full bg-[#f1f5f9] px-2.5 py-0.5 text-xs font-semibold text-[#64748b]">
            Pedagogy Metrics
          </span>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-[#64748b]">
          Share of successful explanations per strategy. This is not model accuracy.
        </p>
      </div>

      {/* Progress Bars for each Strategy */}
      <div className="mt-6 space-y-4">
        {methods.map((method) => {
          const percent = method.effectivenessPercent;
          return (
            <div
              key={method.id}
              onClick={() => onSelectMethod(method)}
              className="group cursor-pointer rounded-xl p-2 transition-colors hover:bg-[#f8fafc]"
            >
              <div className="flex items-center gap-4">
                {/* Strategy Name */}
                <div className="w-24 shrink-0 text-sm font-bold text-[#1e293b] group-hover:text-[#0284c7] transition-colors">
                  {method.name}
                </div>

                {/* Progress Track */}
                <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-[#e5eff6]">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${percent}%`,
                      backgroundColor: percent > 0 ? method.color : '#cbd5e1',
                    }}
                  />
                </div>

                {/* Percentage value */}
                <div className="w-10 shrink-0 text-right text-sm font-bold text-[#1e293b]">
                  {percent}%
                </div>
              </div>

              {/* Subtext info on hover/when active */}
              {method.totalAttempts > 0 && percent > 0 && (
                <div className="mt-1 flex justify-end text-[11px] text-[#94a3b8]">
                  <span>
                    {method.successfulUses} resolved / {method.totalAttempts} total uses
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footnote note */}
      <div className="mt-auto pt-5">
        <p className="text-xs text-[#94a3b8] leading-normal border-t border-[#f1f5f9] pt-4">
          Note: Computed as wins / total counted uses. A &lsquo;win&rsquo; is recorded when the student expresses resolution following that specific strategy.
        </p>
      </div>
    </div>
  );
}

interface DashboardViewProps {
  onStartChat?: () => void;
}

export function DashboardView({ onStartChat }: DashboardViewProps) {
  const metricCards = [
    {
      label: 'CURRENT LEVEL',
      value: 'Normal',
      valueColor: 'text-emerald-500',
      subtext: 'No topic in progress',
    },
    {
      label: 'CONCEPTS LEARNED',
      value: '0',
      valueColor: 'text-ink',
      subtext: 'Understood in the voice tutor',
    },
    {
      label: 'WEAK TOPICS',
      value: '1',
      valueColor: 'text-ink',
      subtext: 'Needed 3 strategies to understand',
    },
    {
      label: 'HELPFUL STYLE',
      value: 'Theory',
      valueColor: 'text-ink',
      subtext: 'Style that worked most often',
    },
  ];

  const strategies = [
    { name: 'Theory', percentage: 0 },
    { name: 'Example', percentage: 0 },
    { name: 'Simplified', percentage: 0 },
    { name: 'Analogy', percentage: 0 },
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-surface p-6 lg:p-8">
      <div className="mx-auto max-w-6xl space-y-5">
        {/* Top 4 Stat Metric Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {metricCards.map((card) => (
            <div
              key={card.label}
              className="rounded-2xl border border-border-subtle bg-surface-raised p-5 shadow-2xs transition-all hover:shadow-xs"
            >
              <p className="text-[11px] font-extrabold uppercase tracking-wider text-ink-faint">
                {card.label}
              </p>
              <p className={`mt-2.5 text-2xl font-black ${card.valueColor}`}>
                {card.value}
              </p>
              <p className="mt-2 text-xs font-medium text-ink-muted">
                {card.subtext}
              </p>
            </div>
          ))}
        </div>

        {/* Bottom Two Detail Cards */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {/* Weakness topic area Card */}
          <div className="rounded-2xl border border-border-subtle bg-surface-raised p-6 shadow-2xs">
            <h3 className="text-base font-bold text-ink sm:text-lg">
              Weakness topic area
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              A topic is stored here as WEAK when the student needed 3 strategies to understand that one question.
            </p>
            <div className="mt-5 border-t border-border-subtle pt-4">
              <div className="flex items-center justify-between py-1.5">
                <span className="text-sm font-semibold text-ink">
                  Object &amp; Class
                </span>
                <span className="rounded-md bg-rose-50 px-2 py-0.5 text-xs font-extrabold tracking-wider text-rose-500 uppercase">
                  WEAK
                </span>
              </div>
            </div>
          </div>

          {/* Observed Strategy Effectiveness Card */}
          <div className="rounded-2xl border border-border-subtle bg-surface-raised p-6 shadow-2xs">
            <h3 className="text-base font-bold text-ink sm:text-lg">
              Observed Strategy Effectiveness
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              Share of successful explanations per strategy. This is not model accuracy.
            </p>
            <div className="mt-5 space-y-3.5">
              {strategies.map((strategy) => (
                <div key={strategy.name} className="flex items-center gap-3">
                  <span className="w-20 text-xs font-semibold text-ink">
                    {strategy.name}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full bg-accent transition-all duration-300"
                      style={{ width: `${strategy.percentage}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-bold text-ink-muted">
                    {strategy.percentage}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

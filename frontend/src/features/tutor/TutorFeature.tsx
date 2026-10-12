/**
 * F1 SHELL — the three-region layout from frontendPlan/03_UI_ARCHITECTURE.md §1.
 *
 * Static placeholder content for now. The send/receive loop arrives at F5, once
 * the mock transport (F3) and the reducer (F4) exist. The regions, the
 * Research Panel toggle and the topic selector are real so the layout can be
 * judged before behaviour is wired in.
 *
 * This is the only public export of the module.
 */

import { useState } from 'react';

import { FALLBACK_TOPICS } from './config/topics';
import { DISPLAY_MAX_CYCLES, env } from './config/env';

export function TutorFeature() {
  const [topic, setTopic] = useState<string>('');
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <div className="flex h-full flex-col bg-surface text-ink">
      <Header
        topic={topic}
        onTopicChange={setTopic}
        panelOpen={panelOpen}
        onTogglePanel={() => setPanelOpen((v) => !v)}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <main className="flex min-h-0 flex-1 flex-col">
          <Transcript topic={topic} />
          <Composer disabled={topic === ''} />
        </main>

        {panelOpen && <ResearchPanel />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function Header({
  topic,
  onTopicChange,
  panelOpen,
  onTogglePanel,
}: {
  topic: string;
  onTopicChange: (t: string) => void;
  panelOpen: boolean;
  onTogglePanel: () => void;
}) {
  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-border-subtle bg-surface-raised px-4 py-3">
      <h1 className="mr-auto text-base font-semibold tracking-tight">Java AI Tutor</h1>

      <label className="flex items-center gap-2 text-sm">
        <span className="text-ink-muted">Topic</span>
        <select
          value={topic}
          onChange={(e) => onTopicChange(e.target.value)}
          className="rounded-md border border-border-subtle bg-surface px-2 py-1.5 text-sm text-ink"
        >
          <option value="">Choose a topic…</option>
          {FALLBACK_TOPICS.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
      </label>

      <button
        type="button"
        onClick={onTogglePanel}
        aria-pressed={panelOpen}
        className="rounded-md border border-border-subtle px-2.5 py-1.5 text-sm text-ink-muted hover:bg-surface-sunken"
      >
        {panelOpen ? 'Hide' : 'Show'} research panel
      </button>
    </header>
  );
}

// ---------------------------------------------------------------------------

function Transcript({ topic }: { topic: string }) {
  return (
    <div
      className="min-h-0 flex-1 overflow-y-auto px-4 py-6"
      aria-live="polite"
      aria-label="Tutoring conversation"
    >
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        {topic === '' ? (
          <EmptyState />
        ) : (
          <>
            <TutorBubble />
            <StudentBubble />
            <p className="text-center text-sm text-ink-faint">
              Conversation loop arrives at F5.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-border-subtle px-6 py-10 text-center">
      <p className="text-ink">Choose a topic to start.</p>
      <p className="mt-2 text-sm text-ink-muted">
        Pick what you want to learn about, then ask a question in your own words.
      </p>
    </div>
  );
}

/** Placeholder tutor message, showing the check question and strategy badge
 *  treatments specified in 03_UI_ARCHITECTURE.md §3. */
function TutorBubble() {
  return (
    <article className="flex flex-col gap-2">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-faint">Tutor</span>
      <div className="rounded-lg rounded-tl-sm border border-border-subtle bg-surface-raised px-4 py-3">
        <p className="leading-relaxed">
          Inheritance lets one class take on the fields and methods of another, so you can
          reuse behaviour instead of repeating it.
        </p>

        <div className="mt-3 border-l-2 border-accent bg-accent-soft px-3 py-2">
          <p className="text-sm">
            <span aria-hidden="true">❓ </span>
            <span className="font-medium">Check:</span> Can you tell me what{' '}
            <code className="font-mono text-[0.9em]">super()</code> does here?
          </p>
        </div>
      </div>
      <StrategyBadge strategy="theory" trigger="default" cycle={1} />
    </article>
  );
}

function StudentBubble() {
  return (
    <article className="flex flex-col items-end gap-2">
      <span className="text-xs font-medium uppercase tracking-wide text-ink-faint">You</span>
      <div className="max-w-[85%] rounded-lg rounded-tr-sm bg-accent px-4 py-3 text-white">
        <p className="leading-relaxed">i dont really get it</p>
      </div>
    </article>
  );
}

function StrategyBadge({
  strategy,
  trigger,
  cycle,
}: {
  strategy: string;
  trigger: string;
  cycle: number;
}) {
  return (
    <p className="font-mono text-xs text-ink-faint">
      {strategy} · {trigger} · cycle {cycle}
    </p>
  );
}

// ---------------------------------------------------------------------------

const STRATEGY_CHIPS = [
  { label: 'Explain the theory', sends: 'explain the theory' },
  { label: 'Show an example', sends: 'show me an example' },
  { label: 'Make it simpler', sends: 'can you make it simpler' },
  { label: 'Real-world analogy', sends: 'give me a real world analogy' },
] as const;

function Composer({ disabled }: { disabled: boolean }) {
  return (
    <div className="border-t border-border-subtle bg-surface-raised px-4 py-3">
      <div className="mx-auto flex max-w-2xl flex-col gap-2.5">
        <div className="flex flex-wrap gap-2">
          {STRATEGY_CHIPS.map((chip) => (
            <button
              key={chip.sends}
              type="button"
              disabled={disabled}
              title={`Sends: "${chip.sends}"`}
              className="rounded-full border border-border-subtle px-3 py-1 text-xs text-ink-muted hover:bg-surface-sunken disabled:opacity-40"
            >
              {chip.label}
            </button>
          ))}
        </div>

        <div className="flex items-end gap-2">
          <textarea
            rows={1}
            disabled={disabled}
            placeholder={disabled ? 'Choose a topic to start' : 'Type your response…'}
            aria-label="Your message"
            className="min-h-[2.75rem] flex-1 resize-none rounded-md border border-border-subtle bg-surface px-3 py-2.5 text-ink placeholder:text-ink-faint disabled:opacity-50"
          />
          <button
            type="button"
            disabled
            title="Voice input arrives in PP2"
            aria-label="Voice input (PP2)"
            className="h-11 rounded-md border border-border-subtle px-3 text-ink-faint disabled:opacity-40"
          >
            <span aria-hidden="true">🎤</span>
          </button>
          <button
            type="button"
            disabled={disabled}
            className="h-11 rounded-md bg-accent px-4 font-medium text-white disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

/** Instrumentation register — monospace numerals, restrained, visibly a
 *  different thing from the student-facing chat (03_UI_ARCHITECTURE.md §5). */
function ResearchPanel() {
  return (
    <aside className="shrink-0 border-t border-border-subtle bg-surface-sunken px-4 py-4 lg:w-80 lg:border-l lg:border-t-0">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
        Research panel
      </h2>

      <div className="mt-4 flex flex-col gap-4 text-sm">
        <PanelCard title="Confusion">
          <div className="flex items-baseline justify-between">
            <span>confused</span>
            <span className="font-mono">0.81</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border-subtle">
            <div className="h-full rounded-full bg-accent" style={{ width: '81%' }} />
          </div>
          <p className="mt-1.5 font-mono text-xs text-ink-faint">source: rule</p>
        </PanelCard>

        <PanelCard title="Strategy">
          <p>example</p>
          <p className="font-mono text-xs text-ink-faint">trigger: confusion</p>
        </PanelCard>

        <PanelCard title={`Cycle 1 of ${DISPLAY_MAX_CYCLES}`}>
          <p className="text-xs text-ink-muted">Used</p>
          <p className="font-mono text-xs">theory, example</p>
          <p className="mt-1.5 text-xs text-ink-muted">Remaining</p>
          <p className="font-mono text-xs">simplified, analogy</p>
        </PanelCard>

        <PanelCard title="Latency">
          <dl className="font-mono text-xs">
            <Row label="classify" value="6 ms" />
            <Row label="llm" value="1840 ms" />
            <Row label="total" value="1902 ms" />
          </dl>
        </PanelCard>

        <PanelCard title="Model">
          <p className="font-mono text-xs">clf-v1.0.0</p>
          <p className="font-mono text-xs text-ink-faint">transport: {env.mode}</p>
        </PanelCard>
      </div>

      <p className="mt-4 text-xs text-ink-faint">
        Placeholder values. Wired to live responses at F8.
      </p>
    </aside>
  );
}

function PanelCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2.5">
      <h3 className="mb-1.5 text-xs font-medium text-ink-muted">{title}</h3>
      {children}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-ink-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

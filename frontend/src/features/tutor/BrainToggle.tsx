// Thinking-mode switch, top right of the chat area.
export function BrainToggle({ on, disabled, onToggle }: { on: boolean; disabled: boolean; onToggle: () => void }) {
  return <button type="button" className={`tutor-brain-toggle ${on ? 'tutor-brain-toggle-on' : ''}`} aria-pressed={on} aria-label="Thinking mode" title="Thinking mode: deeper answers, 1–3 minutes each" disabled={disabled} onClick={onToggle}>
    <svg viewBox="0 0 24 24" fill={on ? 'currentColor' : 'none'} fillOpacity={on ? 0.22 : 0} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9.5 4.5A3 3 0 0 0 6.6 7 3.2 3.2 0 0 0 5 12a3.3 3.3 0 0 0 1.6 4.8A3 3 0 0 0 9.5 20 2.5 2.5 0 0 0 12 17.5v-11A2.5 2.5 0 0 0 9.5 4.5Z" />
      <path d="M14.5 4.5A3 3 0 0 1 17.4 7 3.2 3.2 0 0 1 19 12a3.3 3.3 0 0 1-1.6 4.8 3 3 0 0 1-2.9 3.2 2.5 2.5 0 0 1-2.5-2.5v-11a2.5 2.5 0 0 1 2.5-2Z" />
      <path d="M9 9.5h1.5M13.5 9.5H15M9 14h1.5M13.5 14H15" />
    </svg>
  </button>;
}

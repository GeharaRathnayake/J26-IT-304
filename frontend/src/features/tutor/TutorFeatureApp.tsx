import { Fragment, lazy, Suspense, useEffect, useRef, useState } from 'react';
import Markdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { DISPLAY_MAX_CYCLES, env } from './config/env';
import { useEpisode } from './useEpisode';
import type { MockFault } from './api/adapter';
import type { Strategy } from './api/types';
import { strategyLabels, strings } from './strings';
import type { LocalAudioTrack } from 'livekit-client';
import { SearchComposer } from './SearchComposer';
import { useMicrophone } from './useMicrophone';
import { useSpeechInput } from './useSpeechInput';
import { inferTopic } from './inferTopic';

// Shader + LiveKit code is heavy; only fetch it the first time voice is opened.
const VoiceAura = lazy(() => import('./VoiceAura'));

// The standalone tutor intentionally has no bottom tab navigation. Keep the
// old helper referenced for compatibility with earlier previews without
// rendering it.
void TutorTabBar;

export function TutorFeatureApp() {
  const episode = useEpisode();
  const [panelOpen, setPanelOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(() => localStorage.getItem('java-tutor.sidebar') !== 'collapsed');
  const [voiceOpen, setVoiceOpen] = useState(false);
  const mic = useMicrophone(voiceOpen);
  // If the microphone cannot be opened, leave voice mode and say why.
  useEffect(() => { if (mic.error) setVoiceOpen(false); }, [mic.error]);
  // Spoken turns are sent like typed ones, flagged as voice so the chat shows a
  // generic "Voice message" instead of the recognised text.
  const speech = useSpeechInput({
    active: voiceOpen,
    paused: episode.state.phase === 'awaiting_tutor' || episode.state.phase === 'closed',
    onUtterance: (text) => {
      const spoken = episode.state.topic ? null : inferTopic(text, episode.topics);
      void episode.send(text, { voice: true, ...(spoken ? { topic: spoken.id } : {}) });
    },
  });
  const topic = episode.state.topic ?? '';
  useEffect(() => { localStorage.setItem('java-tutor.sidebar', sidebarOpen ? 'expanded' : 'collapsed'); }, [sidebarOpen]);
  const composerDisabled = episode.state.phase === 'awaiting_tutor' || episode.state.phase === 'closed';
  // Clicking empty space in the main area puts the caret in the composer.
  // Controls, links and text the student is selecting are left alone.
  const focusComposer = (event: React.MouseEvent<HTMLElement>) => {
    if (event.target instanceof Element && event.target.closest('button, a, input, select, textarea, summary, [role="listbox"]')) return;
    if (window.getSelection()?.toString()) return;
    event.currentTarget.querySelector<HTMLTextAreaElement>('.tutor-composer textarea')?.focus();
  };
  return <div className="flex h-full min-h-screen flex-row bg-surface text-ink">
    <TutorSidebar open={sidebarOpen} topic={topic} panelOpen={panelOpen} onTopicChange={episode.chooseTopic} onHome={() => { setPanelOpen(false); setSidebarOpen(true); }} onToggle={() => setSidebarOpen((value) => !value)} onNewTopic={() => episode.reset()} onResearch={() => { setPanelOpen((value) => !value); setSidebarOpen(false); }} onDemoChat={() => episode.chooseTopic('inheritance')} />
      {panelOpen && <ResearchPanel episode={episode} />}
      <div className="flex min-w-0 flex-1 flex-col" onClick={() => { if (sidebarOpen) setSidebarOpen(false); }}>
      <VoicePanel open={voiceOpen} track={mic.track} />
      {voiceOpen && !speech.supported && <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900" role="status">Speech recognition isn&rsquo;t available in this browser, so spoken messages can&rsquo;t be sent. Try Chrome or Edge.</div>}
      {mic.error && <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900" role="alert">{mic.error}</div>}
      {episode.healthStatus === 'unreachable' && <div className="flex items-center justify-between border-b border-red-300 bg-red-50 px-4 py-2 text-sm text-red-900" role="alert"><span>Can&rsquo;t reach the tutor service.</span><button className="rounded border border-red-400 px-2 py-1" onClick={episode.retryHealth}>Retry</button></div>}
      {episode.health && !episode.health.llm_reachable && <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900" role="status">Running with template responses.</div>}
      {episode.state.error?.kind === 'model_unavailable' && <div className="flex items-center justify-between border-b border-red-300 bg-red-50 px-4 py-2 text-sm text-red-900" role="alert"><span>Tutor service unavailable.</span><button className="rounded border border-red-400 px-2 py-1" onClick={episode.retryHealth}>Retry</button></div>}
        <div className="flex min-h-0 flex-1 flex-col"><main className="tutor-main flex min-h-0 min-w-0 flex-1 flex-col" onClick={focusComposer}><Transcript episode={episode} voice={voiceOpen} /><SearchComposer topics={episode.topics} topic={topic} onTopicChange={episode.chooseTopic} onEngage={() => undefined} onDisengage={() => undefined} voiceActive={voiceOpen} voiceTrack={mic.track} onVoiceToggle={() => setVoiceOpen((value) => !value)} onVoiceClose={() => setVoiceOpen(false)} idle={episode.state.messages.length === 0} disabled={composerDisabled} sendDisabled={composerDisabled} draftOnFailure={episode.state.error ? [...episode.state.messages].reverse().find((m) => m.role === 'student' && m.failed)?.text ?? '' : ''} onSend={episode.send} /></main></div>
    </div>
  </div>;
}

function TutorSidebar({ open, topic, panelOpen, onTopicChange, onHome, onToggle, onNewTopic, onResearch, onDemoChat }: { open: boolean; topic: string; panelOpen: boolean; onTopicChange: (topic: string) => void; onHome: () => void; onToggle: () => void; onNewTopic: () => void; onResearch: () => void; onDemoChat: () => void }) {
  const [showMore, setShowMore] = useState(false);
  const recentChats = [
    ['inheritance', 'Understanding inheritance'],
    ['loops', 'Why loops repeat'],
    ['arrays', 'Working with arrays'],
    ['classes_and_objects', 'Classes and objects'],
    ['exception_handling', 'Handling exceptions'],
    ['polymorphism', 'Polymorphism basics'],
  ] as const;
  const visibleChats = showMore ? recentChats : recentChats.slice(0, 5);
  return <aside className={`tutor-sidebar ${open ? 'tutor-sidebar-open' : 'tutor-sidebar-collapsed'}`} aria-label="Tutor navigation">
    <button type="button" className="tutor-sidebar-icon tutor-sidebar-home" onClick={onHome} aria-label="Home" title="Home">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3.5 10.5 8.5-7 8.5 7" /><path d="M5.5 9.5V20h13V9.5" /><path d="M9.5 20v-6h5v6" /></svg>
      {open && <span>Home</span>}
    </button>
    <div className="tutor-sidebar-navigation">
    <button type="button" className="tutor-sidebar-icon" onClick={onToggle} aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'} title={open ? 'Collapse sidebar' : 'Expand sidebar'}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 4v16" /></svg>
      {open && <span>Sidebar</span>}
    </button>
    {open && <div className="tutor-sidebar-divider" />}
    <button type="button" className="tutor-sidebar-icon" onClick={onNewTopic} aria-label="Start a new chat" title="Start a new chat">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h8" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" /><path d="M14 6l3 3" /></svg>
      {open && <span>New chat</span>}
    </button>
    {open && <div className="tutor-past-chats"><p className="tutor-sidebar-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M5 5h14v14H5z" /><path d="M9 9h6M9 13h4" /></svg><span>Recent</span></p>{visibleChats.map(([id, label]) => <button key={id} type="button" className={`tutor-past-chat ${topic === id ? 'tutor-past-chat-active' : ''}`} onClick={id === 'inheritance' ? onDemoChat : () => onTopicChange(id)}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7a2.5 2.5 0 0 1-2.5 2.5H11l-4.5 3v-3.4a2.5 2.5 0 0 1-1.5-2.3z" /></svg><span><span className="tutor-past-chat-title">{label}</span><span className="tutor-past-chat-meta">Java tutoring</span></span></button>)}<button type="button" className="tutor-show-more" onClick={() => setShowMore((value) => !value)}>{showMore ? 'Show less' : 'Show more'}</button></div>}
    {!open && <div className="tutor-sidebar-collapsed-tools"><button type="button" className="tutor-sidebar-icon" onClick={onToggle} aria-label="Recent chats" title="Recent chats"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M5 5h14v14H5z" /><path d="M9 9h6M9 13h4" /></svg></button></div>}
    <button type="button" className={`tutor-sidebar-icon tutor-sidebar-research ${panelOpen ? 'tutor-sidebar-research-active' : ''}`} onClick={onResearch} aria-pressed={panelOpen} aria-label="Research panel" title="Research panel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M4 19V5M4 19h17" /><path d="M8 16v-4M12 16V8M16 16v-7M20 16v-3" /></svg>{open && <span>Research</span>}</button>
    </div>
  </aside>;
}

function VoicePanel({ open, track }: { open: boolean; track: LocalAudioTrack | null }) {
  // The panel height collapses to zero when closed so it never pushes the
  // layout. The aura slides down on open and back up on close (240ms each), so
  // it stays mounted until the exit finishes.
  const [mounted, setMounted] = useState(open);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (open) {
      setMounted(true);
      const frame = requestAnimationFrame(() => requestAnimationFrame(() => setShown(true)));
      return () => cancelAnimationFrame(frame);
    }
    setShown(false);
    const timer = window.setTimeout(() => setMounted(false), 260);
    return () => window.clearTimeout(timer);
  }, [open]);
  return <section className={`tutor-voice-panel ${open ? 'tutor-voice-panel-open' : ''}`} aria-label="Voice input" aria-hidden={!open}>
    <div className="tutor-voice-panel-inner">
      {mounted && <div className={`tutor-voice-aura-wrap ${shown ? 'tutor-voice-aura-wrap-shown' : ''}`}><Suspense fallback={null}><VoiceAura track={track} /></Suspense></div>}
    </div>
  </section>;
}

function Transcript({ episode, voice }: { episode: ReturnType<typeof useEpisode>; voice: boolean }) {
  const { state, send, reset } = episode;
  // The welcome copy stays put until the first message is sent, then drifts up
  // and fades over 240ms. It stays mounted (out of flow) just long enough to
  // finish that exit.
  const hasMessages = state.messages.length > 0;
  const welcomeGone = hasMessages || voice;
  const [emptyMounted, setEmptyMounted] = useState(!welcomeGone);
  const exitTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    window.clearTimeout(exitTimer.current);
    if (!welcomeGone) setEmptyMounted(true);
    else exitTimer.current = window.setTimeout(() => setEmptyMounted(false), 240);
    return () => window.clearTimeout(exitTimer.current);
  }, [welcomeGone]);
  if (voice) return <VoiceResponse state={state} />;
  return <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-28 pt-6" aria-live="polite" aria-label="Tutoring conversation"><div className="relative mx-auto flex max-w-2xl flex-col gap-5">{(emptyMounted || !welcomeGone) && <div className={`tutor-empty-state ${welcomeGone ? 'tutor-empty-state-leaving' : ''}`}><EmptyState /></div>}{state.messages.map((message) => message.role === 'student' ? <StudentBubble key={message.id} message={message} /> : <TutorBubble key={message.id} message={message} />)}{state.phase === 'awaiting_tutor' && <PendingIndicator />}{state.phase === 'awaiting_cycle_decision' && <CycleOffer onSend={send} />}{state.phase === 'closed' && <div className="flex items-center justify-between rounded-lg border border-accent/30 bg-accent-soft px-4 py-3"><span className="text-sm">Episode complete.</span><button className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white" onClick={reset}>Start a new chat</button></div>}{state.error && state.error.kind !== 'model_unavailable' && <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert"><p>{state.error.studentMessage}</p><p className="mt-2 text-xs">Your message is still available in the composer.</p></div>}</div></div>;
}
// Voice mode: the conversation area becomes the tutor's response area. Replies
// from this voice session stack up, each separated from the previous one by a
// divider, and the student can scroll back through them. The newest reply is
// revealed word by word, as if spoken; one already on screen when voice mode
// opened is shown in full. The view follows new text unless scrolled up.
const REVEAL_WORDS_PER_SECOND = 6;
function VoiceResponse({ state }: { state: ReturnType<typeof useEpisode>['state'] }) {
  const tutorReplies = state.messages.filter((message) => message.role === 'tutor');
  const latest = tutorReplies.at(-1);
  // The reply on screen when voice mode opened is where this session starts.
  const startId = useRef(latest?.id);
  const startAt = startId.current ? Math.max(0, tutorReplies.findIndex((message) => message.id === startId.current)) : 0;
  const replies = tutorReplies.slice(startAt);
  const words = latest ? latest.text.split(/(\s+)/) : [];
  const total = words.length;
  const seenReply = useRef(latest?.id);
  const [shown, setShown] = useState(total);
  useEffect(() => {
    if (!latest || latest.id === seenReply.current) { setShown(total); return; }
    setShown(0);
    // The split keeps whitespace tokens, so one word is two tokens; ticks are 250ms.
    const step = Math.max(2, Math.round((REVEAL_WORDS_PER_SECOND / 4) * 2));
    const timer = window.setInterval(() => setShown((count) => {
      if (count + step >= total) { window.clearInterval(timer); seenReply.current = latest.id; return total; }
      return count + step;
    }), 250);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latest?.id]);

  const scroller = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const onScroll = () => {
    const el = scroller.current;
    if (el) following.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };
  useEffect(() => {
    const el = scroller.current;
    if (el && following.current) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [shown, latest?.id, state.phase]);

  // Assistive tech: the text grows every 250ms while it is revealed, which a live
  // region would re-announce on every tick. So the scroller is NOT a live region,
  // the reply being revealed is aria-hidden, and a separate polite region says
  // "thinking" while waiting and then reads the finished reply exactly once.
  const revealing = Boolean(latest) && shown < total;
  const finishedNewReply = latest && !revealing && latest.id !== startId.current ? latest : null;
  return <div ref={scroller} onScroll={onScroll} className="min-h-0 flex-1 overflow-y-auto px-4 pb-28 pt-6" aria-label="Tutor response">
    <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
      {state.phase === 'awaiting_tutor' ? 'The tutor is thinking.' : finishedNewReply && <Markdown rehypePlugins={[rehypeHighlight]} key={finishedNewReply.id}>{finishedNewReply.text}</Markdown>}
    </div>
    <div className="tutor-voice-response mx-auto max-w-2xl">
      {replies.map((reply, index) => <Fragment key={reply.id}>
        {index > 0 && <hr className="tutor-voice-divider" />}
        <div className="text-lg leading-relaxed" aria-hidden={reply.id === latest?.id && revealing ? true : undefined}><Markdown rehypePlugins={[rehypeHighlight]}>{reply.id === latest?.id ? words.slice(0, shown).join('') : reply.text}</Markdown></div>
      </Fragment>)}
      {state.phase === 'awaiting_tutor' && <div aria-hidden="true">{replies.length > 0 && <hr className="tutor-voice-divider" />}<PendingIndicator /></div>}
    </div>
  </div>;
}
function EmptyState() { return <div className="flex flex-col items-center px-6 py-16 text-center"><div className="tutor-empty-star mb-4" aria-hidden="true">✦</div><p className="tutor-empty-title">Ready to learn Java?</p><p className="mt-2 max-w-md text-base leading-6 text-ink-muted">Choose a topic below and ask a question in your own words. I’ll explain it step by step.</p></div>; }
function StudentBubble({ message }: { message: { text: string; failed?: boolean; voice?: boolean } }) {
  // Voice messages are shown as a generic placeholder, not the recognised text.
  return <article className="flex flex-col items-end gap-2">{!message.voice && <span className="text-xs font-bold uppercase tracking-wide text-ink-faint">You</span>}<div className={`tutor-message tutor-message-student max-w-[85%] border px-4 py-3 ${message.failed ? 'tutor-message-failed' : 'border-[#f6d6df] bg-[#fdf4f7] text-ink'}`}>{message.voice
    ? <p className="flex items-center gap-2 leading-relaxed"><svg className="tutor-voice-message-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><rect x="8" y="3" width="8" height="12" rx="4" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></svg>Voice message</p>
    : <p className="whitespace-pre-wrap leading-relaxed">{message.text}</p>}</div>{message.failed && <span className="text-xs text-red-700">Not sent — edit or press Send to retry</span>}</article>;
}
// The tutor's reply is plain text on the page, not a chat bubble.
function TutorBubble({ message }: { message: { text: string; strategy?: Strategy | null; trigger?: string | null; cycle?: number; fallback?: boolean } }) { const parts = message.text.split(/\n\s*\*\*Check:\*\*\s*/); return <article className="flex flex-col gap-2"><div className="tutor-reply max-w-none text-base leading-relaxed"><Markdown rehypePlugins={[rehypeHighlight]}>{parts[0]}</Markdown>{parts[1] && <div className="mt-3 border-t border-border-subtle pt-3 text-sm"><span aria-hidden="true" className="text-accent">❓ </span><span className="font-bold text-accent">Check:</span> {parts[1]}</div>}{message.fallback && <p className="mt-3 text-xs text-accent">template response</p>}</div>{message.strategy && message.trigger && <p className="font-mono text-xs text-ink-faint">{message.strategy} · {message.trigger} · cycle {message.cycle ?? 1}</p>}</article>; }
function PendingIndicator() { return <div className="flex items-center gap-2 text-sm text-ink-muted"><span className="pending-dot" aria-hidden="true" />Thinking…</div>; }
function CycleOffer({ onSend }: { onSend: (message: string) => Promise<void> }) { return <div className="rounded-lg border border-accent/30 bg-accent-soft p-4"><p className="text-sm">{strings.cycleOffer}</p><div className="mt-3 flex flex-wrap gap-2"><button onClick={() => void onSend('yes')} className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white">Yes, explain it another way</button><button onClick={() => void onSend('no')} className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2 text-sm">No, I’ll move on</button></div></div>; }
function TutorTabBar({ panelOpen, onResearch }: { panelOpen: boolean; onResearch: () => void }) { return <nav className="tutor-tabbar grid grid-cols-4 px-6 py-2" aria-label="Primary navigation"><button className="tutor-tab tutor-tab-active flex flex-col items-center justify-center gap-1 text-[11px] font-semibold" aria-current="page"><svg className="tutor-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z" /><path d="M9 21v-7h6v7" /></svg><span>Tutor</span></button><button className="tutor-tab flex flex-col items-center justify-center gap-1 text-[11px] font-semibold" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}><svg className="tutor-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.7-3.2 3.1-5 7-5s6.3 1.8 7 5" /></svg><span>Profile</span></button><button className={`tutor-tab flex flex-col items-center justify-center gap-1 text-[11px] font-semibold ${panelOpen ? 'tutor-tab-active' : ''}`} onClick={onResearch} aria-pressed={panelOpen}><svg className="tutor-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M4 19V5M4 19h17" /><path d="M8 16v-4M12 16V8M16 16v-7M20 16v-3" /></svg><span>Insights</span></button><button className="tutor-tab flex flex-col items-center justify-center gap-1 text-[11px] font-semibold" onClick={() => document.querySelector<HTMLSelectElement>('[aria-label="Choose a Java topic"]')?.focus()}><svg className="tutor-tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.7 1.7-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.2h-2.4v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1L8 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H6v-2.4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L7.3 8 9 6.3l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V5h2.4v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1L19 8l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.2v2.4h-.2a1.7 1.7 0 0 0-1.5 1Z" /></svg><span>Settings</span></button></nav>; }

function ResearchPanel({ episode }: { episode: ReturnType<typeof useEpisode> }) { const { state, health, fault, setFault } = episode; const response = state.lastResponse; const confusion = response?.confusion; const used = state.serverState?.strategies_used ?? []; const counted = used.filter((u) => u.trigger !== 'request'); const remaining = (['theory', 'example', 'simplified', 'analogy'] as Strategy[]).filter((s) => !used.some((u) => u.strategy === s)); const latency = response?.meta.latency_ms; return <aside className="tutor-research-sidebar shrink-0 overflow-y-auto px-3 py-4"><div className="tutor-research-sidebar-heading"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M4 19V5M4 19h17" /><path d="M8 16v-4M12 16V8M16 16v-7M20 16v-3" /></svg><h2>Research</h2><span>{env.mode}</span></div><div className="mt-4 flex flex-col gap-3 text-sm"><PanelCard title="Confusion"><div className="flex justify-between"><span>{confusion?.label ?? '—'}</span><span className="font-mono">{confusion ? confusion.probability.toFixed(2) : '—'}</span></div><div className="mt-1.5 h-1.5 rounded-full bg-border-subtle"><div className="h-full rounded-full bg-accent" style={{ width: `${(confusion?.probability ?? 0) * 100}%` }} /></div><p className="mt-1.5 font-mono text-xs text-ink-faint">source: {confusion?.source ?? '—'}</p></PanelCard><PanelCard title="Strategy"><p>{response?.strategy ? strategyLabels[response.strategy] : '—'}</p><p className="font-mono text-xs text-ink-faint">trigger: {response?.trigger ?? '—'}{response?.detected_request ? ` · requested: ${response.detected_request}` : ''}</p></PanelCard><PanelCard title={`Cycle ${state.serverState?.cycle ?? 1} of ${DISPLAY_MAX_CYCLES}`}><p className="text-xs text-ink-muted">Used ({counted.length})</p><p className="font-mono text-xs">{counted.map((u) => u.strategy).join(', ') || '—'}</p><p className="mt-1.5 text-xs text-ink-muted">Remaining</p><p className="font-mono text-xs">{remaining.join(', ') || '—'}</p></PanelCard><PanelCard title="Latency"><Row label="classify" value={latency ? `${latency.classify} ms` : '—'} /><Row label="llm" value={latency ? `${latency.llm} ms` : '—'} /><Row label="total" value={latency ? `${latency.total} ms` : '—'} />{latency && <p className="mt-2 text-right font-mono text-[10px] text-ink-faint">budget: 3000 ms</p>}</PanelCard><PanelCard title="Model"><p className="font-mono text-xs">{response?.meta.model_version ?? health?.model_version ?? '—'}</p><p className="font-mono text-xs text-ink-faint">{response?.meta.llm ?? '—'}</p>{response?.meta.fallback && <p className="mt-1 text-xs text-amber-700">template fallback</p>}</PanelCard>{state.episodeLog && <PanelCard title="Episode log"><div className="space-y-1 font-mono text-xs"><p>outcome: {state.episodeLog.outcome}</p><p>counted: {state.episodeLog.counted_strategies}</p><p>requested: {state.episodeLog.requested_strategies}</p><p>winning: {state.episodeLog.winning_strategy ?? '—'}</p><p>is_weak: {String(state.episodeLog.is_weak)}</p></div><details className="mt-2"><summary className="cursor-pointer text-xs text-ink-muted">View JSON</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-[10px]">{JSON.stringify(state.episodeLog, null, 2)}</pre></details></PanelCard>}{env.mode === 'mock' && <PanelCard title="Fault switch"><select value={fault} onChange={(e) => setFault(e.target.value as MockFault)} className="w-full rounded border border-border-subtle bg-surface px-2 py-1 text-xs" aria-label="Mock fault switch"><option value="none">None</option><option value="503">503 unavailable</option><option value="504">504 timeout</option><option value="fallback">Template fallback</option><option value="slow">Slow response</option><option value="malformed">Malformed payload</option></select></PanelCard>}</div></aside>; }
function PanelCard({ title, children }: { title: string; children: React.ReactNode }) { return <section className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2.5"><h3 className="mb-1.5 text-xs font-medium text-ink-muted">{title}</h3>{children}</section>; }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex justify-between font-mono text-xs"><span className="text-ink-muted">{label}</span><span>{value}</span></div>; }

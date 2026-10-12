import { Fragment, lazy, Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { LocalAudioTrack } from 'livekit-client';
import { inferTopic } from './inferTopic';

type Topic = { id: string; label: string };

const VoiceWave = lazy(() => import('./VoiceWave'));

type SearchComposerProps = {
  topics: Topic[];
  topic: string;
  onTopicChange: (topic: string) => void;
  onEngage: () => void;
  onDisengage: () => void;
  idle: boolean;
  disabled: boolean;
  sendDisabled: boolean;
  onSend: (message: string, options?: { topic?: string }) => Promise<void>;
  draftOnFailure: string;
  voiceActive: boolean;
  voiceTrack: LocalAudioTrack | null;
  onVoiceToggle: () => void;
  onVoiceClose: () => void;
};

// Composer geometry, defined once. Both the rendered padding and the idle
// measurement probe derive from these so they cannot drift apart.
const MAX_LINES = 6;
const SINGLE_LINE_BOX = 40;
const LINE_HEIGHT = 22;
const MAX_HEIGHT = MAX_LINES * LINE_HEIGHT + 14;
const TOPIC_BUTTON_WIDTH = 38;
const VOICE_BUTTON_RIGHT = 52;
const VOICE_BUTTON_WIDTH = 44;
const CONTROL_GAP = 8;
// The topic button sits at the left in idle mode; once the box grows it drops
// to the bottom row and the text uses the same 14px margin on both sides.
const IDLE_LEFT_RESERVE = TOPIC_BUTTON_WIDTH + 20;
const MULTILINE_LEFT_RESERVE = 14;
const IDLE_RIGHT_RESERVE = VOICE_BUTTON_RIGHT + VOICE_BUTTON_WIDTH + CONTROL_GAP;
const MULTILINE_RIGHT_RESERVE = 14;
// composerW is measured on .tutor-composer-inner: 8px padding x2 + 1px border x2.
const INNER_CHROME = 8 * 2 + 1 * 2;
const TEXT_WIDTH_OFFSET = INNER_CHROME + MULTILINE_LEFT_RESERVE + MULTILINE_RIGHT_RESERVE;
const FLIP_TOLERANCE = 14;
// Voice mode shrinks the bar to a pill: just the wave and the stop button.
const VOICE_PILL_LEFT = 14;

// Insert the topic label at the selection, padded with spaces so it reads as
// its own word. The caret lands after the space that follows the label.
function insertTopic(text: string, start: number, end: number, label: string) {
  const before = text.slice(0, start);
  const after = text.slice(end);
  const lead = before !== '' && !/\s$/.test(before) ? ' ' : '';
  const trail = /^\s/.test(after) ? '' : ' ';
  return { text: `${before}${lead}${label}${trail}${after}`, caret: before.length + lead.length + label.length + 1 };
}

export function SearchComposer({ topics, topic, onTopicChange, onEngage, onDisengage, idle, disabled, sendDisabled, onSend, draftOnFailure, voiceActive, voiceTrack, onVoiceToggle, onVoiceClose }: SearchComposerProps) {
  const [draft, setDraft] = useState('');
  const [topicPickerOpen, setTopicPickerOpen] = useState(false);
  const topicPickerRef = useRef<HTMLDivElement>(null);
  const [composerW, setComposerW] = useState(320);
  const [autoH, setAutoH] = useState(0);
  const [dynamicMode, setDynamicMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mirrorRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const charsPerLine = Math.max(6, Math.floor((composerW - TEXT_WIDTH_OFFSET) / 11));
  const estimatedLines = draft.split('\n').reduce((count, line) => count + Math.max(1, Math.ceil(line.length / charsPerLine)), 0);
  const singleLine = draft.length === 0 || (!dynamicMode && !draft.includes('\n'));
  // Font step uses the monotonic estimate, never the measurement, which is
  // downstream of the font size and would oscillate.
  const compact = !singleLine && estimatedLines >= 4;
  const rawLines = autoH ? Math.max(1, Math.round(autoH / LINE_HEIGHT)) : estimatedLines;
  const lineCount = Math.min(MAX_LINES, Math.max(1, singleLine ? 1 : rawLines));
  const textHeight = singleLine ? SINGLE_LINE_BOX : Math.min(MAX_HEIGHT, Math.max(autoH, lineCount * LINE_HEIGHT) + 8);
  const atCap = !singleLine && rawLines >= MAX_LINES;
  const effectiveLineHeight = singleLine ? SINGLE_LINE_BOX : LINE_HEIGHT;
  // Voice mode docks the bar down, like once a conversation has started.
  const raised = idle && !voiceActive;
  // Topics live in the draft as ordinary text wherever the student put them,
  // and several can be present. `topic` is the one chosen last; the others stay
  // as highlighted keywords. A label counts while its exact text is in the draft,
  // so surrounding spaces can be deleted freely; editing the label itself turns
  // it back into plain text.
  const topicLabel = topics.find((item) => item.id === topic)?.label ?? '';
  const topicActive = topicLabel !== '' && draft.includes(topicLabel);
  const labels = useMemo(() => topics.map((item) => item.label).filter(Boolean), [topics]);
  // A draft that is only a topic label (what picking a topic produces) is a valid
  // message: "Loops" asks the tutor to teach loops.
  const hasContent = draft.trim().length > 0;
  // The mirror draws labels in real bold, which is wider than the regular
  // glyphs the textarea lays out. Tighten each bold word's letter-spacing so it
  // takes exactly the regular width and the two layers stay aligned everywhere.
  const tokenSpacing = useMemo(() => {
    const spacing = new Map<string, number>();
    const ctx = document.createElement('canvas').getContext('2d');
    if (!ctx) return spacing;
    const family = getComputedStyle(textareaRef.current ?? document.body).fontFamily;
    const size = compact ? 15 : parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    labels.forEach((label) => label.split(' ').forEach((word) => {
      if (!word || spacing.has(word)) return;
      ctx.font = `400 ${size}px ${family}`;
      const regular = ctx.measureText(word).width;
      ctx.font = `700 ${size}px ${family}`;
      spacing.set(word, (regular - ctx.measureText(word).width) / word.length);
    }));
    return spacing;
  }, [labels, compact]);
  // Earliest label occurrence at or after `from` (longest wins a tie).
  const nextLabel = (text: string, from: number) => {
    let best: { at: number; label: string } | null = null;
    for (const label of labels) {
      const at = text.indexOf(label, from);
      if (at !== -1 && (!best || at < best.at || (at === best.at && label.length > best.label.length))) best = { at, label };
    }
    return best;
  };
  const mirrorContent = (): ReactNode => {
    const out: ReactNode[] = [];
    let at = 0;
    for (let hit = nextLabel(draft, 0); hit; hit = nextLabel(draft, at)) {
      if (hit.at > at) out.push(draft.slice(at, hit.at));
      out.push(<Fragment key={hit.at}>{hit.label.split(' ').map((word, w) => <Fragment key={w}>{w > 0 ? ' ' : ''}<span className="tutor-composer-topic-token" style={{ letterSpacing: tokenSpacing.get(word) }}>{word}</span></Fragment>)}</Fragment>);
      at = hit.at + hit.label.length;
    }
    out.push(draft.slice(at));
    return out;
  };

  useEffect(() => {
    if (draftOnFailure) setDraft(draftOnFailure);
  }, [draftOnFailure]);

  useEffect(() => {
    const composer = innerRef.current;
    if (!composer) return;
    const updateWidth = () => {
      const width = composer.getBoundingClientRect().width;
      if (width > 150) setComposerW(width);
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(composer);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!topicPickerOpen) return;
    const closeOnOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && !topicPickerRef.current?.contains(target)) {
        setTopicPickerOpen(false);
      }
    };
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    return () => document.removeEventListener('pointerdown', closeOnOutsidePointer);
  }, [topicPickerOpen]);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const previous = { rows: textarea.rows, height: textarea.style.height, paddingLeft: textarea.style.paddingLeft, paddingRight: textarea.style.paddingRight, lineHeight: textarea.style.lineHeight };
    textarea.rows = 1;
    // Measure the real content height in the current layout mode. Collapsing
    // to 0 first lets scrollHeight shrink as well as grow.
    textarea.style.height = '0px';
    const measured = textarea.scrollHeight;

    // Then measure the hypothetical idle layout (both buttons reserved). This
    // decides the flip to dynamic mode and is stable regardless of the
    // current mode.
    textarea.style.paddingLeft = `${IDLE_LEFT_RESERVE}px`;
    textarea.style.paddingRight = `${IDLE_RIGHT_RESERVE}px`;
    textarea.style.lineHeight = `${SINGLE_LINE_BOX}px`;
    textarea.style.height = '0px';
    const idleHeight = textarea.scrollHeight;
    const wrapsIdle = draft.includes('\n') || idleHeight > SINGLE_LINE_BOX + FLIP_TOLERANCE;

    textarea.rows = previous.rows || 1;
    textarea.style.height = previous.height;
    textarea.style.paddingLeft = previous.paddingLeft;
    textarea.style.paddingRight = previous.paddingRight;
    textarea.style.lineHeight = previous.lineHeight;

    if (measured && Math.abs(measured - autoH) > 1) setAutoH(measured);
    if (wrapsIdle !== dynamicMode) {
      if (!wrapsIdle) setAutoH(0);
      setDynamicMode(wrapsIdle);
    }
  }, [draft, composerW, dynamicMode, effectiveLineHeight, compact]); // autoH omitted: this effect writes it

  const placeCaret = (position: number) => requestAnimationFrame(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.focus();
    textarea.setSelectionRange(position, position);
  });

  // Insert the label at the caret (keeping any topics already in the draft),
  // unless that label is already in the draft.
  const addTopic = (text: string, label: string) => {
    if (text.includes(label)) return { text, caret: text.indexOf(label) + label.length + 1 };
    const textarea = textareaRef.current;
    return insertTopic(text, textarea?.selectionStart ?? text.length, textarea?.selectionEnd ?? text.length, label);
  };

  const selectTopic = (item: Topic) => {
    const next = addTopic(draft, item.label);
    setDraft(next.text);
    onTopicChange(item.id);
    setTopicPickerOpen(false);
    placeCaret(next.caret);
  };

  // Topic changed from elsewhere (sidebar, header select, new topic): make sure
  // the draft carries its label. Clearing the topic leaves typed labels as text.
  const syncedLabel = useRef(topicLabel);
  const skipTopicSync = useRef(false);
  useEffect(() => {
    const previous = syncedLabel.current;
    syncedLabel.current = topicLabel;
    if (previous === topicLabel || topicLabel === '') return;
    if (skipTopicSync.current) { skipTopicSync.current = false; return; }
    setDraft((current) => addTopic(current, topicLabel).text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicLabel]);

  const submit = () => {
    const text = draft.trim();
    if (!text || !hasContent || sendDisabled) return;
    // No topic picked: take it from the words (e.g. "explain loops"). If the
    // message names none it is sent as a general chat; no topic is required.
    const inferred = topic ? null : inferTopic(text, topics);
    setDraft('');
    setAutoH(0);
    setDynamicMode(false);
    if (inferred) skipTopicSync.current = true; // the topic came from the message itself
    void onSend(text, inferred ? { topic: inferred.id } : undefined);
  };

  return <div className={`tutor-composer px-4 ${raised ? 'tutor-composer-idle' : ''} ${voiceActive ? 'tutor-composer-voice' : ''}`}>
    <div ref={innerRef} className="tutor-composer-inner mx-auto max-w-2xl bg-surface-raised">
      <div className={`tutor-composer-content ${!singleLine ? 'tutor-composer-multiline' : ''}`}>
        <div ref={topicPickerRef} className="tutor-topic-picker-wrap">
          <button type="button" onMouseDown={(event) => event.preventDefault()} className={`tutor-composer-topic-button ${topicPickerOpen ? 'tutor-composer-topic-button-active' : ''}`} onClick={() => { onEngage(); setTopicPickerOpen((value) => !value); }} aria-label="Choose a Java topic" aria-expanded={topicPickerOpen} title="Choose a Java topic">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" /><circle cx="18" cy="18" r="2" /></svg>
          </button>
          {topicPickerOpen && <div className="tutor-topic-picker" role="listbox" aria-label="Java topics">{topics.map((item) => <button key={item.id} type="button" role="option" onMouseDown={(event) => event.preventDefault()} aria-selected={topic === item.id} className={topic === item.id ? 'tutor-topic-option tutor-topic-option-active' : 'tutor-topic-option'} onClick={() => selectTopic(item)}>{item.label}</button>)}</div>}
        </div>
        <div className={`tutor-composer-field ${voiceActive ? 'tutor-composer-field-voice' : ''}`}>
          <textarea ref={textareaRef} rows={1} value={draft} onChange={(event) => {
            onEngage();
            onVoiceClose();
            const next = event.currentTarget.value;
            // The label itself was edited: it is plain text now. Only drop the
            // topic before the first message, since changing it restarts the
            // conversation.
            if (topicActive && !next.includes(topicLabel) && idle) {
              // Fall back to another topic still in the text, else clear.
              const remaining = nextLabel(next, 0);
              onTopicChange(topics.find((item) => item.label === remaining?.label)?.id ?? '');
            }
            setDraft(next);
          }} onFocus={() => { onEngage(); }} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(); } }} onScroll={(event) => { if (mirrorRef.current) mirrorRef.current.scrollTop = event.currentTarget.scrollTop; }} onBlur={() => { onDisengage(); }} disabled={disabled || voiceActive} placeholder={disabled ? 'Tutor is responding…' : 'Type your response…'} aria-label="Your message" style={{ height: textHeight, lineHeight: `${effectiveLineHeight}px`, padding: `0 ${singleLine ? IDLE_RIGHT_RESERVE : MULTILINE_RIGHT_RESERVE}px 0 ${singleLine ? IDLE_LEFT_RESERVE : MULTILINE_LEFT_RESERVE}px`, fontSize: compact ? 15 : undefined, overflowY: atCap ? 'auto' : 'hidden' }} className={`resize-none tutor-composer-input-ghost placeholder:text-ink-faint disabled:opacity-50 ${compact ? 'tutor-composer-input-compact' : ''}`} />
        <div ref={mirrorRef} aria-hidden="true" className={`tutor-composer-mirror ${disabled ? 'tutor-composer-mirror-disabled' : ''}`} style={{ height: textHeight, lineHeight: `${effectiveLineHeight}px`, padding: `0 ${singleLine ? IDLE_RIGHT_RESERVE : MULTILINE_RIGHT_RESERVE}px 0 ${singleLine ? IDLE_LEFT_RESERVE : MULTILINE_LEFT_RESERVE}px`, fontSize: compact ? 15 : undefined, overflowY: 'hidden' }}>{mirrorContent()}{'\u200b'}</div>
        {voiceActive && <div className="tutor-composer-wave" style={{ left: VOICE_PILL_LEFT, right: VOICE_BUTTON_WIDTH + CONTROL_GAP }}><Suspense fallback={null}><VoiceWave track={voiceTrack} /></Suspense></div>}
        </div>
        <button type="button" onClick={onVoiceToggle} aria-pressed={voiceActive} disabled={disabled} title={voiceActive ? 'Stop voice input' : 'Voice input'} aria-label={voiceActive ? 'Stop voice input' : 'Voice input'} className="tutor-voice-button disabled:opacity-40">{voiceActive
          ? <svg className="tutor-voice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
          : <svg className="tutor-voice-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><rect x="8" y="3" width="8" height="12" rx="4" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></svg>}</button>
        <button type="button" onClick={submit} disabled={sendDisabled || !hasContent} aria-label="Send message" className="tutor-send-button bg-accent font-medium text-white disabled:opacity-40"><svg className="tutor-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5" /><path d="m6 11 6-6 6 6" /></svg></button>
      </div>
    </div>
  </div>;
}

import { useEffect, useRef } from 'react';

// Minimal typing for the browser's (prefixed) Web Speech API.
interface SpeechResultList { length: number; [index: number]: { isFinal: boolean; 0: { transcript: string } } }
interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { resultIndex: number; results: SpeechResultList }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  abort: () => void;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function recognitionCtor(): SpeechRecognitionCtor | undefined {
  const scope = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition;
}

// Turns the student's speech into finished utterances while `active`.
// Results heard while `paused` (the tutor is replying) are ignored. Note: in
// Chrome and Edge the audio is processed by the browser vendor's speech service.
export function useSpeechInput({ active, paused, onUtterance }: { active: boolean; paused: boolean; onUtterance: (text: string) => void }) {
  const supported = recognitionCtor() !== undefined;
  const pausedRef = useRef(paused);
  const onUtteranceRef = useRef(onUtterance);
  pausedRef.current = paused;
  onUtteranceRef.current = onUtterance;

  useEffect(() => {
    const Ctor = recognitionCtor();
    if (!active || !Ctor) return;
    const recognition = new Ctor();
    let stopped = false;
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.onresult = (event) => {
      if (pausedRef.current) return;
      let text = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result?.isFinal) text += result[0].transcript;
      }
      text = text.trim();
      if (text) onUtteranceRef.current(text);
    };
    // The service ends on silence; keep listening until voice mode closes,
    // unless the browser refused the microphone.
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') stopped = true;
    };
    recognition.onend = () => {
      if (stopped) return;
      window.setTimeout(() => { if (!stopped) { try { recognition.start(); } catch { /* already started */ } } }, 250);
    };
    try { recognition.start(); } catch { /* already started */ }
    return () => {
      stopped = true;
      recognition.onend = null;
      recognition.abort();
    };
  }, [active]);

  return { supported };
}

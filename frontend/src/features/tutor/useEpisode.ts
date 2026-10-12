import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { createTransport, loadTopics, type TutorTransport } from './api/adapter';
import { TutorError } from './api/errors';
import { getMockFault, setMockFault, type MockFault } from './api/mockTransport';
import type { TopicOption } from './api/types';
import { episodeReducer, newEpisode } from './reducer';
import { turnInputFor } from './episodeRules';

// Slug used when the student chats without choosing a topic. NOTE: the tutor
// service validates topic slugs (422 for unknown ones), so it must accept this
// value for no-topic chats to work against the real backend.
export const GENERAL_TOPIC = 'general';

export function useEpisode() {
  const transport = useMemo(() => createTransport(), []);
  const [state, dispatch] = useReducer(episodeReducer, null, () => newEpisode());
  const [topics, setTopics] = useState<TopicOption[]>([]);
  const [health, setHealth] = useState<Awaited<ReturnType<TutorTransport['health']>> | null>(null);
  const [fault, setFaultState] = useState<MockFault>(getMockFault());
  useEffect(() => { void loadTopics(transport).then(setTopics); void transport.health().then(setHealth).catch(() => undefined); }, [transport]);
  const chooseTopic = useCallback((topic: string) => dispatch({ type: 'TOPIC_CHANGED', topic }), []);
  const send = useCallback(async (message: string, options?: { voice?: boolean; topic?: string }) => {
    // A topic named in the message wins; otherwise the chosen one; otherwise a
    // general chat. Switching topic starts a fresh episode.
    if (!message.trim() || state.phase === 'awaiting_tutor' || state.phase === 'closed') return;
    const topic = options?.topic ?? state.topic ?? GENERAL_TOPIC;
    if (topic !== state.topic) dispatch({ type: 'TOPIC_CHANGED', topic });
    const id = crypto.randomUUID();
    dispatch({ type: 'SEND_STARTED', message, id, voice: options?.voice });
    try {
      const response = await transport.sendTurn(turnInputFor(state, topic, message));
      dispatch({ type: 'SEND_SUCCEEDED', response, tutorId: crypto.randomUUID() });
    } catch (error) {
      const tutorError = error instanceof TutorError ? error : new TutorError('unknown', 'Unexpected tutor error', { cause: error });
      if (import.meta.env.DEV && (tutorError.kind === 'contract' || tutorError.kind === 'validation')) console.error(tutorError);
      dispatch({ type: 'SEND_FAILED', error: tutorError });
    }
  }, [state, transport]);
  const setFault = useCallback((next: MockFault) => { setMockFault(next); setFaultState(next); }, []);
  const retryHealth = useCallback(() => { void transport.health().then(setHealth).catch(() => undefined); }, [transport]);
  return { state, topics, health, transport, fault, setFault, chooseTopic, send, retryHealth, reset: () => dispatch({ type: 'RESET' }), clearError: () => dispatch({ type: 'RETRY_CLEARED' }) };
}

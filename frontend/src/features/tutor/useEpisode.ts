import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { createTransport, loadTopics, type TutorTransport } from './api/adapter';
import { TutorError } from './api/errors';
import { getMockFault, setMockFault, type MockFault } from './api/mockTransport';
import type { TopicOption } from './api/types';
import { episodeReducer, newEpisode } from './reducer';
import { createSendLatch, GENERAL_TOPIC, probeHealth, resolveTurnTopic, runExclusive, turnInputFor, type HealthStatus } from './episodeRules';

export { GENERAL_TOPIC };

export function useEpisode() {
  const transport = useMemo(() => createTransport(), []);
  const [state, dispatch] = useReducer(episodeReducer, null, () => newEpisode());
  const [topics, setTopics] = useState<TopicOption[]>([]);
  // The send path needs the loaded list synchronously and a way to wait for it.
  const loadedTopics = useRef<TopicOption[] | null>(null);
  const topicsReady = useRef<Promise<TopicOption[]>>(Promise.resolve([]));
  const [health, setHealth] = useState<Awaited<ReturnType<TutorTransport['health']>> | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');
  const [fault, setFaultState] = useState<MockFault>(getMockFault());
  const checkHealth = useCallback(() => {
    setHealthStatus('checking');
    void probeHealth(transport).then((result) => { setHealth(result.health); setHealthStatus(result.status); });
  }, [transport]);
  useEffect(() => {
    topicsReady.current = loadTopics(transport).then((list) => { loadedTopics.current = list; setTopics(list); return list; });
    checkHealth();
  }, [transport, checkHealth]);
  // Checked and set synchronously, so two sends raised from the same render
  // (which both read the same captured `state.phase`) cannot both go out.
  const sendLatch = useRef(createSendLatch());
  const chooseTopic = useCallback((topic: string) => dispatch({ type: 'TOPIC_CHANGED', topic }), []);
  const send = useCallback(async (message: string, options?: { voice?: boolean; topic?: string }) => {
    // A topic named in the message wins; otherwise the chosen one; otherwise a
    // general chat. Switching topic starts a fresh episode.
    if (!message.trim() || state.phase === 'awaiting_tutor' || state.phase === 'closed') return;
    await runExclusive(sendLatch.current, async () => {
      const topic = await resolveTurnTopic({ explicit: options?.topic, current: state.topic, message, topics: loadedTopics.current, topicsReady: topicsReady.current });
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
    });
  }, [state, transport]);
  const setFault = useCallback((next: MockFault) => { setMockFault(next); setFaultState(next); }, []);
  return { state, topics, health, healthStatus, transport, fault, setFault, chooseTopic, send, retryHealth: checkHealth, reset: () => dispatch({ type: 'RESET' }) };
}

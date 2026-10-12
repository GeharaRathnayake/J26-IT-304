import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { createTransport, loadTopics, type TutorTransport } from './api/adapter';
import { TutorError } from './api/errors';
import { getMockFault, setMockFault, type MockFault } from './api/mockTransport';
import type { TopicOption } from './api/types';
import { FALLBACK_TOPICS } from './config/topics';
import { episodeReducer, newEpisode } from './reducer';
import { createGenerationGuard, createSendLatch, GENERAL_TOPIC, probeHealth, resolveTurnTopic, runExclusive, turnInputFor, type HealthStatus } from './episodeRules';

export { GENERAL_TOPIC };

export function useEpisode() {
  const transport = useMemo(() => createTransport(), []);
  const [state, dispatch] = useReducer(episodeReducer, null, () => newEpisode());
  // Seeded, never empty: the send path reads this synchronously, so an empty
  // initial list would have forced it to wait for GET /topics (see
  // resolveTurnTopic). The fetched list replaces it when it arrives.
  const [topics, setTopics] = useState<TopicOption[]>(() => [...FALLBACK_TOPICS]);
  const loadedTopics = useRef<TopicOption[]>([...FALLBACK_TOPICS]);
  const [health, setHealth] = useState<Awaited<ReturnType<TutorTransport['health']>> | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');
  const [fault, setFaultState] = useState<MockFault>(getMockFault());
  const checkHealth = useCallback(() => {
    setHealthStatus('checking');
    void probeHealth(transport).then((result) => { setHealth(result.health); setHealthStatus(result.status); });
  }, [transport]);
  useEffect(() => {
    void loadTopics(transport).then((list) => { loadedTopics.current = list; setTopics(list); });
    checkHealth();
  }, [transport, checkHealth]);
  // Checked and set synchronously, so two sends raised from the same render
  // (which both read the same captured `state.phase`) cannot both go out.
  const sendLatch = useRef(createSendLatch());
  // Invalidates in-flight responses whenever the episode is replaced.
  const generation = useRef(createGenerationGuard());
  const chooseTopic = useCallback((topic: string) => { generation.current.bump(); dispatch({ type: 'TOPIC_CHANGED', topic }); }, []);
  const reset = useCallback(() => { generation.current.bump(); dispatch({ type: 'RESET' }); }, []);
  const send = useCallback(async (message: string, options?: { voice?: boolean; topic?: string }) => {
    // A topic named in the message wins; otherwise the chosen one; otherwise a
    // general chat. Switching topic starts a fresh episode.
    if (!message.trim() || state.phase === 'awaiting_tutor' || state.phase === 'closed') return;
    await runExclusive(sendLatch.current, async () => {
      // Synchronous: the student must see their message before any network work.
      const topic = resolveTurnTopic({ explicit: options?.topic, current: state.topic, message, topics: loadedTopics.current });
      // TOPIC_CHANGED resets the episode (newEpisode clears messages), so it must
      // come before SEND_STARTED or it would delete the bubble just added. The
      // generation token is captured after it, so this send is not its own victim.
      if (topic !== state.topic) { generation.current.bump(); dispatch({ type: 'TOPIC_CHANGED', topic }); }
      const sendGeneration = generation.current.current();
      const id = crypto.randomUUID();
      dispatch({ type: 'SEND_STARTED', message, id, voice: options?.voice });
      try {
        const response = await transport.sendTurn(turnInputFor(state, topic, message));
        if (generation.current.isStale(sendGeneration)) return;
        dispatch({ type: 'SEND_SUCCEEDED', response, tutorId: crypto.randomUUID() });
      } catch (error) {
        const tutorError = error instanceof TutorError ? error : new TutorError('unknown', 'Unexpected tutor error', { cause: error });
        if (import.meta.env.DEV && (tutorError.kind === 'contract' || tutorError.kind === 'validation')) console.error(tutorError);
        if (generation.current.isStale(sendGeneration)) return;
        dispatch({ type: 'SEND_FAILED', error: tutorError });
      }
    });
  }, [state, transport]);
  const setFault = useCallback((next: MockFault) => { setMockFault(next); setFaultState(next); }, []);
  return { state, topics, health, healthStatus, transport, fault, setFault, chooseTopic, send, retryHealth: checkHealth, reset };
}

import type { EpisodeLog, HistoryTurn, TutorResponse, TutorState } from './api/types';
import type { TutorError } from './api/errors';

export type Phase = 'idle' | 'awaiting_tutor' | 'awaiting_student' | 'awaiting_cycle_decision' | 'closed';
export interface UIMessage { id: string; role: 'student' | 'tutor'; text: string; strategy?: TutorResponse['strategy']; trigger?: TutorResponse['trigger']; cycle?: number; fallback?: boolean; failed?: boolean; voice?: boolean; transcript?: string; audioUrl?: string; }
export interface EpisodeUI { phase: Phase; topic: string | null; messages: UIMessage[]; history: HistoryTurn[]; serverState: TutorState | null; lastResponse: TutorResponse | null; episodeLog: EpisodeLog | null; error: TutorError | null;  }

export type EpisodeAction =
  | { type: 'TOPIC_CHANGED'; topic: string }
  | { type: 'SEND_STARTED'; message: string; id: string; voice?: boolean }
  | { type: 'SEND_SUCCEEDED'; response: TutorResponse; tutorId: string }
  | { type: 'SEND_FAILED'; error: TutorError }
  | { type: 'RESET' };

export function phaseFromResponse(response: TutorResponse): Phase {
  if (response.action === 'resolved' || response.action === 'end_unresolved') return 'closed';
  if (response.updated_state.awaiting_cycle_confirmation) return 'awaiting_cycle_decision';
  return 'awaiting_student';
}
export function newEpisode(topic: string | null = null): EpisodeUI { return { phase: topic ? 'awaiting_student' : 'idle', topic, messages: [], history: [], serverState: null, lastResponse: null, episodeLog: null, error: null }; }

export function episodeReducer(state: EpisodeUI, action: EpisodeAction): EpisodeUI {
  switch (action.type) {
    case 'TOPIC_CHANGED': return newEpisode(action.topic);
    case 'SEND_STARTED': return { ...state, phase: 'awaiting_tutor', error: null, messages: [...state.messages, { id: action.id, role: 'student', text: action.message, ...(action.voice ? { voice: true } : {}) }] , history: [...state.history, { role: 'student', text: action.message, ts: new Date().toISOString() }] };
    case 'SEND_SUCCEEDED': {
      const res = action.response;
      const tutor: UIMessage = { id: action.tutorId, role: 'tutor', text: res.response, strategy: res.strategy, trigger: res.trigger, cycle: res.updated_state.cycle, fallback: res.meta.fallback };
      const history = res.strategy ? [...state.history, { role: 'tutor' as const, text: res.response, strategy: res.strategy, ts: new Date().toISOString() }] : [...state.history, { role: 'tutor' as const, text: res.response, ts: new Date().toISOString() }];
      return { ...state, phase: phaseFromResponse(res), messages: [...state.messages, tutor], history, serverState: res.updated_state, lastResponse: res, episodeLog: res.episode_log, error: null };
    }
    case 'SEND_FAILED': return { ...state, phase: state.serverState?.awaiting_cycle_confirmation ? 'awaiting_cycle_decision' : state.serverState || state.topic ? 'awaiting_student' : 'idle', error: action.error, messages: state.messages.map((m) => m.id === state.messages.at(-1)?.id && m.role === 'student' ? { ...m, failed: true } : m) };
    case 'RESET': return newEpisode();
  }
}

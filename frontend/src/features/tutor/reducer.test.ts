import { describe, expect, it } from 'vitest';
import { episodeReducer, newEpisode, phaseFromResponse } from './reducer';
import type { TutorResponse } from './api/types';

const state = { episode_id: 'ep_1', cycle: 1, strategies_used: [{ strategy: 'theory' as const, trigger: 'default' as const }], awaiting_cycle_confirmation: false, prior_explanations: ['one'] };
function response(overrides: Partial<TutorResponse> = {}): TutorResponse { return { request_id: 'r', confusion: { label: 'confused', probability: .8, source: 'model' }, detected_request: null, action: 'explain', strategy: 'example', trigger: 'confusion', response: 'body', updated_state: state, episode_log: null, meta: { model_version: 'm', llm: 'l', latency_ms: { classify: 1, llm: 2, total: 3 } }, ...overrides }; }

describe('episode state machine', () => {
  it('keeps a cycle offer pending for an unclear reply', () => {
    expect(phaseFromResponse(response({ action: 'clarify', strategy: null, trigger: null, updated_state: { ...state, awaiting_cycle_confirmation: true } }))).toBe('awaiting_cycle_decision');
  });
  it('closes only on resolved or end_unresolved', () => {
    expect(phaseFromResponse(response({ action: 'resolved', episode_log: {} as never }))).toBe('closed');
    expect(phaseFromResponse(response({ action: 'end_unresolved', episode_log: {} as never }))).toBe('closed');
  });
  it('keeps the server state opaque and history contract-shaped', () => {
    const initial = newEpisode('inheritance');
    const started = episodeReducer(initial, { type: 'SEND_STARTED', id: 'm1', message: 'I am confused' });
    const received = response();
    const finished = episodeReducer(started, { type: 'SEND_SUCCEEDED', tutorId: 't1', response: received });
    expect(finished.serverState).toBe(received.updated_state);
    expect(finished.history).toEqual(expect.arrayContaining([{ role: 'student', text: 'I am confused', ts: expect.any(String) }, { role: 'tutor', text: 'body', strategy: 'example', ts: expect.any(String) }]));
  });
  it('retains a failed student message for retry', () => {
    const started = episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'm1', message: 'help' });
    const failed = episodeReducer(started, { type: 'SEND_FAILED', error: new Error('network') as never });
    expect(failed.messages.at(-1)?.failed).toBe(true);
  });
});

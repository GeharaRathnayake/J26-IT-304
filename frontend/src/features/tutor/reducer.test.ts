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
  it('clears the error when a resend starts, so an identical repeated failure re-triggers the composer restore', () => {
    // The composer restores the failed text from an error-gated prop. That only
    // fires again for the same text because SEND_STARTED nulls the error between
    // two failures; this pins that dependency (review finding F3 was not a bug).
    const err = new Error('503') as never;
    const first = episodeReducer(episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'm1', message: 'hello' }), { type: 'SEND_FAILED', error: err });
    expect(first.error).toBe(err);
    const resent = episodeReducer(first, { type: 'SEND_STARTED', id: 'm2', message: 'hello' });
    expect(resent.error).toBeNull();
    const second = episodeReducer(resent, { type: 'SEND_FAILED', error: err });
    expect(second.error).toBe(err);
    expect(second.messages.filter((m) => m.failed).map((m) => m.id)).toEqual(['m1', 'm2']);
  });
  it('returns to awaiting_student, not idle, when the first send on a topic fails', () => {
    // newEpisode(topic) starts in awaiting_student; a failed first send must not
    // demote it to idle just because no server state exists yet (review F8.1).
    const started = episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'm1', message: 'help' });
    const failed = episodeReducer(started, { type: 'SEND_FAILED', error: new Error('503') as never });
    expect(failed.phase).toBe('awaiting_student');
    // With no topic at all, idle is still right.
    const noTopic = episodeReducer(episodeReducer(newEpisode(), { type: 'SEND_STARTED', id: 'm2', message: 'help' }), { type: 'SEND_FAILED', error: new Error('503') as never });
    expect(noTopic.phase).toBe('idle');
  });
});

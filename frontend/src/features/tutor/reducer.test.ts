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

describe('a superseded response corrupts the fresh episode (point 5)', () => {
  // Reproduction of the defect the generation guard prevents. The sidebar's
  // "New chat" (TutorFeatureApp.tsx:47, onNewTopic -> episode.reset()) has no
  // phase guard, so it fires during `awaiting_tutor`. These two tests show the
  // damage the reducer does if the in-flight response is still dispatched, and
  // are the reason useEpisode captures a generation token and drops stale ones.
  function inFlightThenNewChat() {
    const sent = episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'm1', message: 'what is a loop' });
    expect(sent.phase).toBe('awaiting_tutor');
    return episodeReducer(sent, { type: 'RESET' });   // student clicks "New chat"
  }

  it('REPRO: dispatching the late response leaves a tutor reply with no question above it', () => {
    const fresh = inFlightThenNewChat();
    expect(fresh.messages).toEqual([]);

    const corrupted = episodeReducer(fresh, { type: 'SEND_SUCCEEDED', response: response(), tutorId: 't1' });

    // The damage: a tutor message alone in a brand-new episode, carrying the
    // previous episode's server state underneath it.
    expect(corrupted.messages).toHaveLength(1);
    expect(corrupted.messages[0]?.role).toBe('tutor');
    expect(corrupted.serverState?.episode_id).toBe(state.episode_id);
    expect(corrupted.topic).toBeNull();
  });

  it('FIX: dropping the stale response leaves the fresh episode untouched', () => {
    const fresh = inFlightThenNewChat();
    // useEpisode returns before dispatching when the guard reports staleness,
    // so the reducer never sees the action at all.
    expect(fresh.messages).toEqual([]);
    expect(fresh.serverState).toBeNull();
    expect(fresh.phase).toBe('idle');
  });
});

describe('the conversation continues after an episode ends (SF1)', () => {
  const resolvedState = { ...state, episode_id: 'ep_1' };
  const newState = { ...state, episode_id: 'ep_2' };

  function resolvedEpisode() {
    let ep = newEpisode('inheritance');
    ep = episodeReducer(ep, { type: 'SEND_STARTED', id: 's1', message: 'one' });
    ep = episodeReducer(ep, { type: 'SEND_SUCCEEDED', tutorId: 't1', response: response({ updated_state: resolvedState }) });
    ep = episodeReducer(ep, { type: 'SEND_STARTED', id: 's2', message: 'two' });
    ep = episodeReducer(ep, { type: 'SEND_SUCCEEDED', tutorId: 't2', response: response({ updated_state: resolvedState }) });
    ep = episodeReducer(ep, { type: 'SEND_STARTED', id: 's3', message: 'three' });
    const log = { episode_id: 'ep_1' } as never;
    ep = episodeReducer(ep, { type: 'SEND_SUCCEEDED', tutorId: 't3', response: response({ action: 'resolved', strategy: null, trigger: null, episode_log: log, updated_state: resolvedState }) });
    return ep;
  }

  it('starts a new episode inside the same conversation when a message is sent from closed', () => {
    const closed = resolvedEpisode();
    expect(closed.phase).toBe('closed');
    const next = episodeReducer(closed, { type: 'SEND_STARTED', id: 's4', message: 'four' });
    expect(next.phase).toBe('awaiting_tutor');
    expect(next.messages).toHaveLength(closed.messages.length + 1);
    expect(next.messages.slice(0, closed.messages.length)).toEqual(closed.messages);
    expect(next.messages.at(-1)).toMatchObject({ id: 's4', role: 'student', text: 'four' });
    expect(next.history).toEqual([{ role: 'student', text: 'four', ts: expect.any(String) }]);
    expect(next.serverState).toBeNull();
    expect(next.lastResponse).toBeNull();
    expect(next.episodeLog).toBe(closed.episodeLog);
    expect(next.episodeLog).not.toBeNull();
    expect(next.topic).toBe('inheritance');
  });

  it('shows all eight messages across the old and the new episode, and the new episode owns the server state', () => {
    const closed = resolvedEpisode();
    expect(closed.messages).toHaveLength(6);
    let ep = episodeReducer(closed, { type: 'SEND_STARTED', id: 's4', message: 'four' });
    ep = episodeReducer(ep, { type: 'SEND_SUCCEEDED', tutorId: 't4', response: response({ updated_state: newState }) });
    expect(ep.messages).toHaveLength(8);
    expect(ep.messages.map((m) => m.role)).toEqual(['student', 'tutor', 'student', 'tutor', 'student', 'tutor', 'student', 'tutor']);
    expect(ep.serverState?.episode_id).toBe('ep_2');
    expect(ep.phase).toBe('awaiting_student');
    expect(ep.history.filter((h) => h.role === 'student')).toHaveLength(1);
  });

  it('leaves a send from any other phase appending to the same episode (unchanged)', () => {
    let ep = episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'a', message: 'one' });
    ep = episodeReducer(ep, { type: 'SEND_SUCCEEDED', tutorId: 't', response: response() });
    const next = episodeReducer(ep, { type: 'SEND_STARTED', id: 'b', message: 'two' });
    expect(next.history).toHaveLength(3);
    expect(next.serverState).toBe(ep.serverState);
  });
});

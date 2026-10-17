import { describe, expect, it } from 'vitest';
import { chatIdFor, parseStore, recordState, titleFor, toStorable, upsertChat, emptyStore, type StoredChat } from './chatStore';
import { episodeReducer, newEpisode, type EpisodeUI } from './reducer';
import { turnInputFor } from './episodeRules';
import type { TutorResponse } from './api/types';

const serverState = { episode_id: 'ep_1', cycle: 1, strategies_used: [{ strategy: 'theory' as const, trigger: 'default' as const }], awaiting_cycle_confirmation: false, prior_explanations: ['one'] };
function response(overrides: Partial<TutorResponse> = {}): TutorResponse { return { request_id: 'r', confusion: { label: 'confused', probability: .8, source: 'rule' }, detected_request: null, action: 'explain', strategy: 'theory', trigger: 'default', response: 'body', updated_state: serverState, episode_log: null, meta: { model_version: 'm', llm: 'l', latency_ms: { classify: 1, llm: 2, total: 3 } }, ...overrides }; }

/** A real three-turn conversation built by the reducer itself. */
function threeTurns(): EpisodeUI {
  let s = newEpisode('inheritance');
  s = episodeReducer(s, { type: 'SEND_STARTED', id: 'm1', message: "I don't understand inheritance" });
  s = episodeReducer(s, { type: 'SEND_SUCCEEDED', tutorId: 't1', response: response() });
  s = episodeReducer(s, { type: 'SEND_STARTED', id: 'm2', message: 'why does that work?' });
  s = episodeReducer(s, { type: 'SEND_SUCCEEDED', tutorId: 't2', response: response({ strategy: 'example', trigger: 'confusion', updated_state: { ...serverState, strategies_used: [...serverState.strategies_used, { strategy: 'example', trigger: 'confusion' }] } }) });
  return s;
}
const chat = (id: string, updatedAt: string): StoredChat => ({ id, title: id, topic: null, updatedAt, state: newEpisode() });

describe('chat titles and ids', () => {
  it('titles a chat by its first student message, cut to 40 characters', () => {
    const s = episodeReducer(newEpisode(), { type: 'SEND_STARTED', id: 'm1', message: '  what   is the difference between an interface and an abstract class in Java?' });
    expect(titleFor(s)).toBe('what is the difference between an interf…');
    expect(titleFor(newEpisode())).toBe('New chat');
  });
  it('takes the id of the first message, so a cleared chat starts a new one', () => {
    expect(chatIdFor(newEpisode())).toBeNull();
    expect(chatIdFor(threeTurns())).toBe('m1');
  });
});

describe('what is saved', () => {
  it('never saves a reply in flight: the last student message is saved as failed, in a waiting phase', () => {
    const inFlight = episodeReducer(threeTurns(), { type: 'SEND_STARTED', id: 'm3', message: 'still lost' });
    expect(inFlight.phase).toBe('awaiting_tutor');
    const saved = toStorable(inFlight);
    expect(saved.phase).toBe('awaiting_student');
    expect(saved.messages.at(-1)).toMatchObject({ id: 'm3', role: 'student', failed: true });
    expect(saved.error).toBeNull();
  });
  it('saves nothing for a chat with no message yet', () => {
    const store = emptyStore();
    expect(recordState(store, newEpisode('loops'), '2026-10-17T00:00:00Z')).toBe(store);
  });
});

describe('the list', () => {
  it('replaces by id, keeps newest first and drops the oldest beyond the cap', () => {
    let store = emptyStore();
    store = upsertChat(store, chat('a', '2026-10-17T01:00:00Z'), 3);
    store = upsertChat(store, chat('b', '2026-10-17T02:00:00Z'), 3);
    store = upsertChat(store, chat('c', '2026-10-17T03:00:00Z'), 3);
    store = upsertChat(store, chat('a', '2026-10-17T04:00:00Z'), 3);
    expect(store.chats.map((c) => c.id)).toEqual(['a', 'c', 'b']);
    store = upsertChat(store, chat('d', '2026-10-17T05:00:00Z'), 3);
    expect(store.chats.map((c) => c.id)).toEqual(['d', 'a', 'c']);
  });
});

describe('reading storage never throws', () => {
  it('turns anything unreadable into an empty store', () => {
    for (const raw of [null, '', '{', '{"version":2,"chats":[]}', '{"version":1}', '"x"', 'null']) {
      expect(parseStore(raw)).toEqual({ version: 1, chats: [] });
    }
  });
  it('drops a malformed chat and keeps the good ones', () => {
    const good = recordState(emptyStore(), threeTurns(), '2026-10-17T00:00:00Z').chats[0];
    const raw = JSON.stringify({ version: 1, chats: [good, { id: 'bad' }] });
    expect(parseStore(raw).chats.map((c) => c.id)).toEqual(['m1']);
  });
});

describe('a refresh keeps the chat and continues its episode', () => {
  it('round-trips through JSON and RESTORE with nothing lost', () => {
    const before = threeTurns();
    const raw = JSON.stringify(recordState(emptyStore(), before, '2026-10-17T00:00:00Z'));
    const restored = episodeReducer(newEpisode(), { type: 'RESTORE', state: parseStore(raw).chats[0]!.state });
    expect(restored.messages).toEqual(before.messages);
    expect(restored.history).toEqual(before.history);
    expect(restored.serverState).toEqual(before.serverState);
    expect(restored.episodeLog).toEqual(before.episodeLog);
    expect(restored.topic).toBe('inheritance');
  });
  it('sends the restored episode state and history on the next turn (same episode)', () => {
    const before = threeTurns();
    const restored = episodeReducer(newEpisode(), { type: 'RESTORE', state: parseStore(JSON.stringify(recordState(emptyStore(), before, 'now'))).chats[0]!.state });
    const input = turnInputFor(restored, 'inheritance', 'i am still lost', false);
    expect(input.state).toEqual(before.serverState);
    expect(input.history).toEqual(before.history);
  });
});

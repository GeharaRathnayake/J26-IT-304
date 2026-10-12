import { describe, expect, it } from 'vitest';
import { createSendLatch, GENERAL_TOPIC, probeHealth, resolveTurnTopic, runExclusive, turnInputFor } from './episodeRules';
import { FALLBACK_TOPICS } from './config/topics';
import { episodeReducer, newEpisode } from './reducer';
import type { TutorState } from './api/types';

const serverState: TutorState = { episode_id: 'ep_old', cycle: 2, strategies_used: [{ strategy: 'theory', trigger: 'default' }], awaiting_cycle_confirmation: false, prior_explanations: ['old'] };

// An episode on `loops` with one finished turn: history and server state present.
function loopsEpisodeWithHistory() {
  const started = episodeReducer(newEpisode('loops'), { type: 'SEND_STARTED', id: 'm1', message: 'what is a loop' });
  return { ...started, serverState, history: [...started.history, { role: 'tutor' as const, text: 'a loop repeats', strategy: 'theory' as const, ts: 't' }] };
}

describe('turnInputFor (F1)', () => {
  it('carries accumulated history and the last state verbatim on the same topic', () => {
    const episode = loopsEpisodeWithHistory();
    const input = turnInputFor(episode, 'loops', 'next');
    expect(input.history).toBe(episode.history);
    expect(input.state).toBe(episode.serverState);
    expect(input).toMatchObject({ topic: 'loops', message: 'next', profile: null });
  });

  it('sends a different topic as a fresh episode: no history, null state', () => {
    const episode = loopsEpisodeWithHistory();
    const input = turnInputFor(episode, 'arrays', 'and arrays?');
    expect(input.topic).toBe('arrays');
    expect(input.history).toEqual([]);
    expect(input.state).toBeNull();
  });

  it('treats the first message of a topic-less episode as a fresh one', () => {
    const input = turnInputFor(newEpisode(), 'general', 'hello');
    expect(input.history).toEqual([]);
    expect(input.state).toBeNull();
  });
});

describe('send latch (F2)', () => {
  it('lets only one of two same-tick calls through', async () => {
    const latch = createSendLatch();
    let started = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const task = async () => { started += 1; await gate; return 'sent'; };
    // Both calls are made before either has a chance to finish: the second sees
    // the latch held, exactly like two handlers firing from one render.
    const first = runExclusive(latch, task);
    const second = runExclusive(latch, task);
    release();
    expect(await first).toBe('sent');
    expect(await second).toBeUndefined();
    expect(started).toBe(1);
  });

  it('releases after completion so the next send is allowed', async () => {
    const latch = createSendLatch();
    await runExclusive(latch, async () => 'one');
    expect(await runExclusive(latch, async () => 'two')).toBe('two');
  });

  it('releases when the task throws, so a failed send does not wedge the composer', async () => {
    const latch = createSendLatch();
    await expect(runExclusive(latch, async () => { throw new Error('network'); })).rejects.toThrow('network');
    expect(await runExclusive(latch, async () => 'retry')).toBe('retry');
  });
});

describe('probeHealth (F6)', () => {
  it('reports ok with the payload when /health answers', async () => {
    const health = { status: 'ok' as const, model_loaded: true, llm_reachable: true, model_version: 'v1' };
    expect(await probeHealth({ health: async () => health })).toEqual({ status: 'ok', health });
  });

  it('reports unreachable (not "nothing wrong") when /health rejects', async () => {
    const result = await probeHealth({ health: async () => { throw new Error('network'); } });
    expect(result).toEqual({ status: 'unreachable', health: null });
  });
});

describe('resolveTurnTopic (F8.4)', () => {
  const list = [...FALLBACK_TOPICS];
  const never = new Promise<typeof list>(() => undefined);

  it('prefers an explicit topic, then the episode topic, without waiting for topics', async () => {
    expect(await resolveTurnTopic({ explicit: 'arrays', current: 'loops', message: 'x', topics: null, topicsReady: never })).toBe('arrays');
    expect(await resolveTurnTopic({ current: 'loops', message: 'x', topics: null, topicsReady: never })).toBe('loops');
  });

  it('waits for GET /topics before inferring, instead of silently sending general', async () => {
    let resolveTopics!: (value: typeof list) => void;
    const topicsReady = new Promise<typeof list>((resolve) => { resolveTopics = resolve; });
    let settled = false;
    const pending = resolveTurnTopic({ current: null, message: 'explain loops', topics: null, topicsReady }).then((id) => { settled = true; return id; });
    await Promise.resolve();
    expect(settled).toBe(false);
    resolveTopics(list);
    expect(await pending).toBe('loops');
  });

  it('infers from an already-loaded list, and falls back to general when nothing is named', async () => {
    expect(await resolveTurnTopic({ current: null, message: 'tell me about arrays', topics: list, topicsReady: never })).toBe('arrays');
    expect(await resolveTurnTopic({ current: null, message: 'hello', topics: list, topicsReady: never })).toBe(GENERAL_TOPIC);
  });
});

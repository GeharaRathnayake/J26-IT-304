import { describe, expect, it } from 'vitest';
import { createGenerationGuard, createSendLatch, GENERAL_TOPIC, probeHealth, resolveTurnTopic, runExclusive, turnInputFor } from './episodeRules';
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

describe('resolveTurnTopic: synchronous, never waits (F8.4 regression)', () => {
  const list = [...FALLBACK_TOPICS];

  it('prefers an explicit topic, then the episode topic', () => {
    expect(resolveTurnTopic({ explicit: 'arrays', current: 'loops', message: 'x', topics: list })).toBe('arrays');
    expect(resolveTurnTopic({ current: 'loops', message: 'x', topics: list })).toBe('loops');
  });

  it('infers from the seeded list, and falls back to general when nothing is named', () => {
    expect(resolveTurnTopic({ current: null, message: 'tell me about arrays', topics: list })).toBe('arrays');
    expect(resolveTurnTopic({ current: null, message: 'hello', topics: list })).toBe(GENERAL_TOPIC);
  });

  // The original defect: topics started as [] and the resolver awaited GET /topics
  // to avoid inferring from an empty list. Seeding removes the need to wait, so
  // this must stay a plain function. A Promise return would reintroduce the
  // dead-air and latch-wedge bugs.
  it('returns a string, not a promise, so no send can be delayed by it', () => {
    const result: unknown = resolveTurnTopic({ current: null, message: 'explain loops', topics: list });
    expect(typeof result).toBe('string');
    expect(result).not.toBeInstanceOf(Promise);
  });
});

describe('generation guard: superseded responses (point 5)', () => {
  it('treats a captured token as current until the episode is replaced', () => {
    const guard = createGenerationGuard();
    const token = guard.current();
    expect(guard.isStale(token)).toBe(false);
    guard.bump();
    expect(guard.isStale(token)).toBe(true);
  });

  it('keeps a token captured after a bump valid, so a send that changes topic is not its own victim', () => {
    const guard = createGenerationGuard();
    guard.bump();                       // send resolves a new topic -> TOPIC_CHANGED
    const token = guard.current();      // captured after, as useEpisode does
    expect(guard.isStale(token)).toBe(false);
  });

  it('invalidates every in-flight send once, not per listener', () => {
    const guard = createGenerationGuard();
    const first = guard.current();
    const second = guard.current();
    guard.bump();
    expect(guard.isStale(first)).toBe(true);
    expect(guard.isStale(second)).toBe(true);
  });
});

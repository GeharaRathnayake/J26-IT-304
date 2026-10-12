import { describe, expect, it } from 'vitest';
import { turnInputFor } from './episodeRules';
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

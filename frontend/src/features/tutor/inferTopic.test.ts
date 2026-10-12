import { describe, expect, it } from 'vitest';
import { inferTopic } from './inferTopic';
import { FALLBACK_TOPICS } from './config/topics';

const topics = [...FALLBACK_TOPICS];
const idOf = (text: string) => inferTopic(text, topics)?.id ?? null;

describe('inferTopic', () => {
  it('finds a topic by label or a longer label word, case-insensitively', () => {
    expect(idOf('please explain LOOPS')).toBe('loops');
    expect(idOf('how do arrays work')).toBe('arrays');
    expect(idOf('what are methods in java')).toBe('methods_and_functions');
  });

  it('returns the topic mentioned earliest', () => {
    expect(idOf('compare arrays and loops')).toBe('arrays');
    expect(idOf('compare loops and arrays')).toBe('loops');
  });

  it('matches whole words only, not substrings of longer words (review F8.3)', () => {
    expect(idOf('this is dysfunctions of my code')).toBeNull();
    expect(idOf('the overloops are odd')).toBeNull();
    expect(idOf('I like subclasses and misinheritance')).toBeNull();
    // the real word still matches next to punctuation
    expect(idOf('loops, please!')).toBe('loops');
  });

  it('handles labels with regex-special characters', () => {
    expect(idOf('how does File I/O work')).toBe('file_io');
    expect(idOf('Variables & Data Types please')).toBe('variables_and_data_types');
  });

  it('returns null when no topic is mentioned', () => {
    expect(idOf('hello there')).toBeNull();
  });
});

import { describe, expect, it } from 'vitest';
import { formatElapsed, nextShown, revealEnabled, TEXT_TICK_MS, TEXT_WORDS_PER_SECOND, tokenize, VOICE_TICK_MS, VOICE_WORDS_PER_SECOND } from './reveal';

describe('nextShown', () => {
  it('pins voice mode: 6 words/s on 250 ms ticks is 3 tokens per tick', () => {
    expect(VOICE_WORDS_PER_SECOND).toBe(6);
    expect(VOICE_TICK_MS).toBe(250);
    expect(nextShown(0, 100, VOICE_WORDS_PER_SECOND, VOICE_TICK_MS)).toBe(3);
    expect(nextShown(3, 100, VOICE_WORDS_PER_SECOND, VOICE_TICK_MS)).toBe(6);
  });

  it('text mode: 35 words/s on 100 ms ticks is 7 tokens per tick', () => {
    expect(nextShown(0, 1000, TEXT_WORDS_PER_SECOND, TEXT_TICK_MS)).toBe(7);
  });

  it('never passes the total, and always advances', () => {
    expect(nextShown(98, 100, TEXT_WORDS_PER_SECOND, TEXT_TICK_MS)).toBe(100);
    expect(nextShown(0, 100, 0.1, 10)).toBe(2);
  });
});

describe('tokenize', () => {
  it('keeps whitespace so joining restores the text', () => {
    const text = 'a loop  repeats\nthings';
    expect(tokenize(text).join('')).toBe(text);
    expect(tokenize('one two')).toEqual(['one', ' ', 'two']);
  });
});

describe('revealEnabled', () => {
  it('is off under reduced motion and on otherwise', () => {
    expect(revealEnabled(true)).toBe(false);
    expect(revealEnabled(false)).toBe(true);
  });
});

describe('formatElapsed', () => {
  it('formats m:ss', () => {
    expect(formatElapsed(0)).toBe('0:00');
    expect(formatElapsed(61_000)).toBe('1:01');
    expect(formatElapsed(600_000)).toBe('10:00');
    expect(formatElapsed(59_999)).toBe('0:59');
  });
});

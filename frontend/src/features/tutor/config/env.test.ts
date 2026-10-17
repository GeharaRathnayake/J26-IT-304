import { describe, expect, it } from 'vitest';
import { effectiveThinking, parseShowThinkingToggle } from './env';

describe('parseShowThinkingToggle', () => {
  it('is true only for "true", trimmed and case-insensitive', () => {
    expect(parseShowThinkingToggle('true')).toBe(true);
    expect(parseShowThinkingToggle(' TRUE ')).toBe(true);
  });
  it('is false for anything else, so a typo keeps the toggle hidden', () => {
    for (const raw of [undefined, '', '1', 'yes', 'false', 'truee', true, null]) expect(parseShowThinkingToggle(raw)).toBe(false);
  });
});

describe('effectiveThinking', () => {
  it('is true only when thinking is on and the toggle is shown', () => {
    expect(effectiveThinking(true, true)).toBe(true);
    expect(effectiveThinking(true, false)).toBe(false);
    expect(effectiveThinking(false, true)).toBe(false);
    expect(effectiveThinking(false, false)).toBe(false);
  });
});

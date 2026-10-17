import { describe, expect, it } from 'vitest';
import { scrollTargetFor, shouldScrollToQuestion } from './scrollToQuestion';

describe('scrollTargetFor', () => {
  it('puts the bubble 16 px below the scroller top by default', () => {
    expect(scrollTargetFor(500, 24)).toBe(508);
    expect(scrollTargetFor(500, 24, 0)).toBe(524);
  });
  it('never goes negative', () => {
    expect(scrollTargetFor(0, 0)).toBe(0);
  });
});

describe('shouldScrollToQuestion', () => {
  it('scrolls only when the content overflows', () => {
    expect(shouldScrollToQuestion(900, 600)).toBe(true);
    expect(shouldScrollToQuestion(600, 600)).toBe(false);
    expect(shouldScrollToQuestion(300, 600)).toBe(false);
  });
});

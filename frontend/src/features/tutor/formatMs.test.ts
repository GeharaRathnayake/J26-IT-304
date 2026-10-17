import { describe, expect, it } from 'vitest';
import { formatMs } from './formatMs';

describe('formatMs', () => {
  it('shows one decimal and the unit', () => {
    expect(formatMs(1.3709999988941476)).toBe('1.4 ms');
    expect(formatMs(4432.243100000051)).toBe('4432.2 ms');
    expect(formatMs(4433.8440999999875)).toBe('4433.8 ms');
    expect(formatMs(0)).toBe('0.0 ms');
  });
  it('shows a dash for a value that is not a finite number', () => {
    expect(formatMs(NaN)).toBe('—');
    expect(formatMs(Infinity)).toBe('—');
  });
});

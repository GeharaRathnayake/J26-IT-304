// Pure pieces of the word-by-word reveal, shared by the voice view and the text
// transcript. Kept free of React so they run in the node test environment.

/** Voice mode reveals as if spoken; text mode types faster. */
export const VOICE_WORDS_PER_SECOND = 6;
export const TEXT_WORDS_PER_SECOND = 35;
export const VOICE_TICK_MS = 250;
export const TEXT_TICK_MS = 100;

/** Tokens keep the whitespace between words, so one word is two tokens. */
export function tokenize(text: string): string[] {
  return text.split(/(\s+)/);
}

/** How many tokens are shown after one more tick. At least one word per tick
 * (two tokens), never past `total`. Voice (6 words/s, 250 ms) gives 3 tokens. */
export function nextShown(shown: number, total: number, wordsPerSecond: number, tickMs: number): number {
  const step = Math.max(2, Math.round(((wordsPerSecond * tickMs) / 1000) * 2));
  return Math.min(total, shown + step);
}

/** Reduced motion shows the whole reply at once. */
export function revealEnabled(reducedMotion: boolean): boolean {
  return !reducedMotion;
}

/** `m:ss` for the thinking-turn wait counter. */
export function formatElapsed(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

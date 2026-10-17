import { useCallback, useEffect, useRef, useState } from 'react';
import { nextShown, revealEnabled, tokenize } from './reveal';

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export { revealEnabled };

/** Reveals the reply `id` word by word. A reply already present when the hook
 * mounted is shown in full; so is every reply when `enabled` is false. A
 * re-render never restarts the animation (the effect depends on `id` only). */
export function useReveal(id: string | undefined, text: string, options: { wordsPerSecond: number; tickMs: number; enabled: boolean }) {
  const tokens = id ? tokenize(text) : [];
  const total = tokens.length;
  const seen = useRef(id);
  const timer = useRef<number | undefined>(undefined);
  const [progress, setProgress] = useState<{ id: string | undefined; shown: number }>({ id, shown: total });
  // A new reply starts at 0 on the very render it arrives, not after an effect,
  // so its full text never flashes before the animation begins.
  const animating = Boolean(id) && options.enabled && id !== seen.current;
  const shown = progress.id === id ? Math.min(progress.shown, total) : animating ? 0 : total;

  useEffect(() => {
    window.clearInterval(timer.current);
    if (!id || !options.enabled || id === seen.current) { setProgress({ id, shown: total }); return; }
    setProgress({ id, shown: 0 });
    timer.current = window.setInterval(() => setProgress((p) => {
      const next = nextShown(p.shown, total, options.wordsPerSecond, options.tickMs);
      if (next >= total) { window.clearInterval(timer.current); seen.current = id; }
      return { id, shown: next };
    }), options.tickMs);
    return () => window.clearInterval(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const finish = useCallback(() => {
    window.clearInterval(timer.current);
    if (id) { seen.current = id; setProgress({ id, shown: total }); }
  }, [id, total]);

  return { tokens, shown, total, revealing: Boolean(id) && shown < total, finish };
}

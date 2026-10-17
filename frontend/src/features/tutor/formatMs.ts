/** A latency for the research panel: one decimal and the unit ("4432.2 ms").
 *  Display only; the measured value in `meta.latency_ms` is never rounded. */
export function formatMs(ms: number): string {
  if (!Number.isFinite(ms)) return '—';
  return `${ms.toFixed(1)} ms`;
}

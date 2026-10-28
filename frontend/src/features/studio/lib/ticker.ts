/** Pure easing/interpolation for `NumberTicker` (docs/studio/N_20_function.md §2.4). */

// cubic-bezier(0.22, 1, 0.36, 1) approximated for a 1D ease-out: good enough for a counter.
export function easeOut(t: number): number {
  const clamped = Math.min(1, Math.max(0, t))
  return 1 - Math.pow(1 - clamped, 3)
}

/** Value at elapsed/duration (ms) between `from` and `to`, eased. */
export function tickerValue(
  from: number,
  to: number,
  elapsedMs: number,
  durationMs: number,
): number {
  if (durationMs <= 0) return to
  const progress = easeOut(elapsedMs / durationMs)
  return from + (to - from) * progress
}

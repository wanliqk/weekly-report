/** `docs/方案设计.md` §8.6: a future month has zero denominator days and a null rate, which the UI renders as `--` rather than `NaN%` or `0%`. */
export function formatCompletionRate(rate: number | null): string {
  return rate === null ? '--' : `${rate}%`
}

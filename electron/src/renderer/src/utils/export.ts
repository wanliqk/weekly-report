import { ApiError } from '../api/client'

/** Extracts `data.invalid_daily_report_day_ids` from a 40001 export-selection rejection, or `null` if the error is unrelated. */
export function invalidExportDayIds(error: unknown): string[] | null {
  if (!(error instanceof ApiError) || error.code !== 40001) {
    return null
  }
  const data = error.data as { invalid_daily_report_day_ids?: unknown }
  if (!Array.isArray(data.invalid_daily_report_day_ids)) {
    return null
  }
  return data.invalid_daily_report_day_ids.filter((id): id is string => typeof id === 'string')
}

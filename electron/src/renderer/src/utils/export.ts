import { ApiError } from '../api/client'

/** Extracts `data.invalid_report_ids` from a 40001 export-selection rejection, or `null` if the error is unrelated. */
export function invalidExportReportIds(error: unknown): string[] | null {
  if (!(error instanceof ApiError) || error.code !== 40001) {
    return null
  }
  const data = error.data as { invalid_report_ids?: unknown }
  if (!Array.isArray(data.invalid_report_ids)) {
    return null
  }
  return data.invalid_report_ids.filter((id): id is string => typeof id === 'string')
}

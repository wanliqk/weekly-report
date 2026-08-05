import { requestBinary, requestData } from './client'
import type { ExportCreateRequest, ExportJobData } from '../types/export'

const DEFAULT_FILE_NAME = 'daily-report-export.xlsx'

export function createDailyReportExport(payload: ExportCreateRequest): Promise<ExportJobData> {
  return requestData({ method: 'POST', url: '/api/v1/daily-report-exports', data: payload })
}

export function getDailyReportExport(jobId: string): Promise<ExportJobData> {
  return requestData({ method: 'GET', url: `/api/v1/daily-report-exports/${jobId}` })
}

export async function downloadDailyReportExportFile(
  jobId: string
): Promise<{ data: ArrayBuffer; fileName: string }> {
  const { data, fileName } = await requestBinary({
    method: 'GET',
    url: `/api/v1/daily-report-exports/${jobId}/file`
  })
  return { data, fileName: fileName ?? DEFAULT_FILE_NAME }
}

import { requestData } from './client'
import type {
  DailyContent,
  DailyReportData,
  DailyReportListData,
  DailyReportQuery
} from '../types/daily-report'

export function listDailyReports(query: DailyReportQuery): Promise<DailyReportListData> {
  return requestData({ method: 'GET', url: '/api/v1/daily-reports', params: query })
}

export function createDailyReport(workDate: string): Promise<DailyReportData> {
  return requestData({
    method: 'POST',
    url: '/api/v1/daily-reports',
    data: { work_date: workDate }
  })
}

export function getDailyReport(reportId: string): Promise<DailyReportData> {
  return requestData({ method: 'GET', url: `/api/v1/daily-reports/${reportId}` })
}

export function saveDailyReport(
  reportId: string,
  version: number,
  content: DailyContent
): Promise<DailyReportData> {
  return requestData({
    method: 'PATCH',
    url: `/api/v1/daily-reports/${reportId}`,
    data: { version, content }
  })
}

export function submitDailyReport(reportId: string, version: number): Promise<DailyReportData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/daily-reports/${reportId}/submit`,
    data: { version }
  })
}

export function archiveDailyReport(reportId: string, version: number): Promise<DailyReportData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/daily-reports/${reportId}/archive`,
    data: { version }
  })
}

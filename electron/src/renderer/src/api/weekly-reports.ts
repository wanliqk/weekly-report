import { requestData } from './client'
import type {
  WeeklyAvailabilityData,
  WeeklyQuery,
  WeeklyReportData,
  WeeklyReportListData
} from '../types/weekly-report'

export function getWeeklyAvailability(weekStart: string): Promise<WeeklyAvailabilityData> {
  return requestData({
    method: 'GET',
    url: '/api/v1/weekly-reports/availability',
    params: { week_start: weekStart }
  })
}

export function listWeeklyReports(query: WeeklyQuery): Promise<WeeklyReportListData> {
  return requestData({ method: 'GET', url: '/api/v1/weekly-reports', params: query })
}

export function generateWeeklyReport(weekStart: string): Promise<WeeklyReportData> {
  return requestData({
    method: 'POST',
    url: '/api/v1/weekly-reports',
    data: { week_start: weekStart }
  })
}

export function getWeeklyReport(reportId: string): Promise<WeeklyReportData> {
  return requestData({ method: 'GET', url: `/api/v1/weekly-reports/${reportId}` })
}

export function saveWeeklyReport(
  reportId: string,
  version: number,
  fields: { supplement: string; next_week_plan: string; risks: string }
): Promise<WeeklyReportData> {
  return requestData({
    method: 'PUT',
    url: `/api/v1/weekly-reports/${reportId}`,
    data: { version, ...fields }
  })
}

export function regenerateWeeklyReport(
  reportId: string,
  version: number
): Promise<WeeklyReportData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/weekly-reports/${reportId}/regenerate`,
    data: { version, confirm_overwrite: true }
  })
}

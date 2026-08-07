import { requestData } from './client'
import type { DailyReportDayDetailData, DailyReportDayMonthData } from '../types/daily-report-day'

export function getMonthSummary(month: string): Promise<DailyReportDayMonthData> {
  return requestData({ method: 'GET', url: '/api/v1/daily-report-days', params: { month } })
}

export function getDayDetail(workDate: string): Promise<DailyReportDayDetailData> {
  return requestData({ method: 'GET', url: `/api/v1/daily-report-days/${workDate}` })
}

export function archiveDay(workDate: string): Promise<DailyReportDayDetailData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/daily-report-days/${workDate}/archive`,
    data: { confirm_archive: true }
  })
}

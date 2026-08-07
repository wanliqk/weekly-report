import type { DailyReportDayMonthItemData } from './daily-report-day'

export interface StatisticsMonthlyData {
  month: string
  effective_date_from: string
  effective_date_to: string
  denominator_days: number
  completed_days: number
  completion_rate: number | null
  daily_report_count: number
  weekly_report_count: number
  current_streak_days: number
  days: DailyReportDayMonthItemData[]
}

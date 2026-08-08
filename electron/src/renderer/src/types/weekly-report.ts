import type { DailyStatus, ProjectListEntry } from './daily-report'

export interface WeeklyDayField {
  field_key: string
  label: string
  value: string | number | string[] | ProjectListEntry[] | null
}

export interface WeeklyDayEntry {
  daily_report_id: string
  submitted_at: string | null
  fields: WeeklyDayField[]
}

export interface WeeklyDay {
  work_date: string
  daily_report_day_id: string
  entries: WeeklyDayEntry[]
}

export interface WeeklyContent {
  days: WeeklyDay[]
  supplement: string
  next_week_plan: string
  risks: string
}

export interface WeeklyAvailabilityDay {
  work_date: string
  status: DailyStatus | null
}

export interface WeeklyAvailabilityData {
  week_start: string
  week_end: string
  days: WeeklyAvailabilityDay[]
  archived_count: number
  non_archived_dates: string[]
  existing_weekly_report_id: string | null
}

export interface WeeklyReportListItemData {
  id: string
  week_start: string
  week_end: string
  version: number
  generated_at: string
  updated_at: string
}

export interface WeeklyReportListData {
  items: WeeklyReportListItemData[]
  page: number
  page_size: number
  total: number
}

export interface WeeklyReportData {
  id: string
  week_start: string
  week_end: string
  content: WeeklyContent
  generated_content: WeeklyContent
  version: number
  generated_at: string
  created_at: string
  updated_at: string
}

export interface WeeklyQuery {
  week_from?: string
  week_to?: string
  page: number
  page_size: number
}

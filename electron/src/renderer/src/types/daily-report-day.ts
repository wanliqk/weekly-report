import type { DailyContent, DailyReportListItemData } from './daily-report'
import type { TemplateFieldData } from './template'

export type DailyReportDayStatus = 'open' | 'archived'

export interface DailyReportDayMonthItemData {
  work_date: string
  day_id: string
  status: DailyReportDayStatus
  draft_count: number
  submitted_count: number
  archived_count: number
  total_count: number
  can_create: boolean
  can_archive: boolean
  archive_disabled_reason: string | null
}

export interface DailyReportDayMonthData {
  month: string
  items: DailyReportDayMonthItemData[]
}

export interface DayArchiveSnapshotEntryData {
  daily_report_id: string
  submitted_at: string
  template_version_id: string
  template_snapshot: TemplateFieldData[]
  content: DailyContent
}

export interface DayArchiveSnapshotData {
  work_date: string
  entries: DayArchiveSnapshotEntryData[]
}

export interface DailyReportDayDetailData {
  work_date: string
  status: DailyReportDayStatus
  draft_count: number
  submitted_count: number
  archived_count: number
  can_archive: boolean
  archive_disabled_reason: string | null
  entries: DailyReportListItemData[]
  archive_snapshot: DayArchiveSnapshotData | null
  archived_at: string | null
}

/** Calendar-cell status derived client-side per `docs/方案设计.md` §8.3: `none` when no `daily_report_days` row exists at all, `mixed` when drafts and submitted entries coexist. */
export type DailyDayCellStatus = 'none' | 'draft' | 'submitted' | 'mixed' | 'archived'

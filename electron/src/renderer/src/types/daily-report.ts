import type { TemplateFieldData } from './template'

export type DailyStatus = 'draft' | 'submitted' | 'archived'
export type DailyFieldValue = string | number | string[] | null
export type DailyContent = Record<string, DailyFieldValue>

export interface DailyRevocationData {
  reason: string
  revoked_at: string
  actor_username: string
}

export interface DailyReportListItemData {
  id: string
  day_id: string
  work_date: string
  status: DailyStatus
  version: number
  updated_at: string
  submitted_at: string | null
  archived_at: string | null
}

export interface DailyReportListData {
  items: DailyReportListItemData[]
  page: number
  page_size: number
  total: number
}

export interface DailyReportData {
  id: string
  day_id: string
  work_date: string
  status: DailyStatus
  template_version_id: string
  template_snapshot: TemplateFieldData[]
  content: DailyContent
  version: number
  submitted_at: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
  last_revocation: DailyRevocationData | null
}

export interface DailyReportCreateData extends DailyReportData {
  created: boolean
}

export interface DailyReportQuery {
  date_from?: string
  date_to?: string
  status?: DailyStatus
  page: number
  page_size: number
}

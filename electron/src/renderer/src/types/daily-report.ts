import type { TemplateFieldData } from './template'

export type DailyStatus = 'draft' | 'submitted' | 'archived'

/**
 * One row of a `PROJECT_LIST` field (`ai-docs/decisions.md` PROD-022,
 * reshaped by PROD-028 and PROD-030). `project`/`content`
 * (工作项目/工作步骤) are required; the other eight are optional
 * free-text tracking details. `category` defaults to `重要`.
 */
export interface ProjectListEntry {
  category: string
  project: string
  content: string
  weight: string
  planned_completion_date: string
  actual_completion_date: string
  owner: string
  assistant: string
  required_resources: string
  completion_notes: string
}

export type DailyFieldValue = string | number | string[] | ProjectListEntry[] | null
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

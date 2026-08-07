export interface AdminDailyReportSubmittedItemData {
  id: string
  owner_id: string
  owner_username: string
  owner_display_name: string
  work_date: string
  submitted_at: string | null
  version: number
}

export interface AdminDailyReportSubmittedListData {
  items: AdminDailyReportSubmittedItemData[]
  page: number
  page_size: number
  total: number
}

export type AdminAuditAction = 'daily_submission_revoked' | 'user_deleted'

export interface AdminAuditEventData {
  id: string
  action: AdminAuditAction
  actor_username_snapshot: string
  target_type: string
  target_id: string
  target_owner_id: string | null
  reason: string
  created_at: string
}

export interface AdminAuditEventListData {
  items: AdminAuditEventData[]
  page: number
  page_size: number
  total: number
}

export interface AdminAuditEventQuery {
  action?: AdminAuditAction
  date_from?: string
  date_to?: string
  page: number
  page_size: number
}

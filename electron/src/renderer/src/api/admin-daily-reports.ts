import { requestData } from './client'
import type {
  AdminAuditEventListData,
  AdminAuditEventQuery,
  AdminDailyReportSubmittedItemData,
  AdminDailyReportSubmittedListData
} from '../types/admin-daily-report'

export function listSubmittedDailyReports(
  page = 1,
  pageSize = 20
): Promise<AdminDailyReportSubmittedListData> {
  return requestData({
    method: 'GET',
    url: '/api/v1/admin/daily-reports/submitted',
    params: { page, page_size: pageSize }
  })
}

export function revokeDailyReportSubmission(
  reportId: string,
  version: number,
  reason: string
): Promise<AdminDailyReportSubmittedItemData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/admin/daily-reports/${reportId}/revoke-submission`,
    data: { version, reason }
  })
}

export function listAuditEvents(query: AdminAuditEventQuery): Promise<AdminAuditEventListData> {
  return requestData({ method: 'GET', url: '/api/v1/admin/audit-events', params: query })
}

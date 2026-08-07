import type { AdminAuditAction } from '../types/admin-daily-report'

export function auditActionLabel(action: AdminAuditAction): string {
  return {
    daily_submission_revoked: '撤销日报提交',
    user_deleted: '删除用户'
  }[action]
}

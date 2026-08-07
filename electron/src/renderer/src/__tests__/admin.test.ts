import { describe, expect, it } from 'vitest'

import { auditActionLabel } from '@renderer/utils/admin'

describe('auditActionLabel', () => {
  it('labels the revoke action', () => {
    expect(auditActionLabel('daily_submission_revoked')).toBe('撤销日报提交')
  })

  it('labels the user-deleted action', () => {
    expect(auditActionLabel('user_deleted')).toBe('删除用户')
  })
})

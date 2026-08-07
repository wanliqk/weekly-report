import { describe, expect, it } from 'vitest'

import { cannotDeleteReasonLabel } from '@renderer/utils/users'

describe('cannotDeleteReasonLabel', () => {
  it('returns null when the account is deletable', () => {
    expect(cannotDeleteReasonLabel(null)).toBeNull()
  })

  it('describes each non-deletable reason', () => {
    expect(cannotDeleteReasonLabel('self')).toContain('当前登录账号')
    expect(cannotDeleteReasonLabel('last_active_admin')).toContain('最后一个有效管理员')
    expect(cannotDeleteReasonLabel('has_business_records')).toContain('停用')
  })
})

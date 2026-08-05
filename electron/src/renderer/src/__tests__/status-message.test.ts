import { describe, expect, it } from 'vitest'

import { formatServiceState } from '@renderer/utils/status-message'

describe('formatServiceState', () => {
  it('returns readable messages for backend states', () => {
    expect(formatServiceState('pending')).toBe('等待桌面进程接入')
    expect(formatServiceState('ready')).toBe('运行正常')
    expect(formatServiceState('failed')).toBe('启动失败')
  })
})

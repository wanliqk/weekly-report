import { describe, expect, it } from 'vitest'

import { ApiError } from '@renderer/api/client'
import { invalidExportDayIds } from '@renderer/utils/export'

describe('invalidExportDayIds', () => {
  it('extracts the string day ids from a 40001 selection rejection', () => {
    const error = new ApiError(40001, '所选日期中存在不属于本人或未归档的记录', 400, {
      invalid_daily_report_day_ids: ['01AAA', '01BBB']
    })

    expect(invalidExportDayIds(error)).toEqual(['01AAA', '01BBB'])
  })

  it('drops non-string entries defensively without throwing', () => {
    const error = new ApiError(40001, 'x', 400, {
      invalid_daily_report_day_ids: ['01AAA', 42, null]
    })

    expect(invalidExportDayIds(error)).toEqual(['01AAA'])
  })

  it('returns null for an unrelated error code', () => {
    const error = new ApiError(40401, '导出任务不存在', 404, {})

    expect(invalidExportDayIds(error)).toBeNull()
  })

  it('returns null when data has no invalid_daily_report_day_ids field', () => {
    const error = new ApiError(40001, 'x', 400, {})

    expect(invalidExportDayIds(error)).toBeNull()
  })

  it('returns null for a non-ApiError value', () => {
    expect(invalidExportDayIds(new Error('boom'))).toBeNull()
  })
})

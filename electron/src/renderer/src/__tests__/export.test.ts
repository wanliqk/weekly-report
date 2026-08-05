import { describe, expect, it } from 'vitest'

import { ApiError } from '@renderer/api/client'
import { invalidExportReportIds } from '@renderer/utils/export'

describe('invalidExportReportIds', () => {
  it('extracts the string report ids from a 40001 selection rejection', () => {
    const error = new ApiError(40001, '所选日报中存在不属于本人或未归档的记录', 400, {
      invalid_report_ids: ['01AAA', '01BBB']
    })

    expect(invalidExportReportIds(error)).toEqual(['01AAA', '01BBB'])
  })

  it('drops non-string entries defensively without throwing', () => {
    const error = new ApiError(40001, 'x', 400, { invalid_report_ids: ['01AAA', 42, null] })

    expect(invalidExportReportIds(error)).toEqual(['01AAA'])
  })

  it('returns null for an unrelated error code', () => {
    const error = new ApiError(40401, '导出任务不存在', 404, {})

    expect(invalidExportReportIds(error)).toBeNull()
  })

  it('returns null when data has no invalid_report_ids field', () => {
    const error = new ApiError(40001, 'x', 400, {})

    expect(invalidExportReportIds(error)).toBeNull()
  })

  it('returns null for a non-ApiError value', () => {
    expect(invalidExportReportIds(new Error('boom'))).toBeNull()
  })
})

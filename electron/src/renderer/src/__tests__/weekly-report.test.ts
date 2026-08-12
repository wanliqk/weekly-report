import { describe, expect, it } from 'vitest'

import { ApiError } from '@renderer/api/client'
import {
  existingWeeklyReportId,
  formatWeeklyFieldValue,
  mondayOfWeek,
  weekEndFor
} from '@renderer/utils/weekly-report'

describe('mondayOfWeek', () => {
  it('returns the same date when it is already a Monday', () => {
    expect(mondayOfWeek('2026-08-03')).toBe('2026-08-03')
  })

  it("snaps a mid-week date back to that week's Monday", () => {
    expect(mondayOfWeek('2026-08-06')).toBe('2026-08-03')
  })

  it("snaps a Sunday back to the same week's Monday, not the next one", () => {
    expect(mondayOfWeek('2026-08-09')).toBe('2026-08-03')
  })

  it('handles a cross-year week', () => {
    expect(mondayOfWeek('2026-01-01')).toBe('2025-12-29')
  })
})

describe('weekEndFor', () => {
  it('returns the following Sunday', () => {
    expect(weekEndFor('2026-08-03')).toBe('2026-08-09')
  })

  it('handles a cross-year week', () => {
    expect(weekEndFor('2025-12-29')).toBe('2026-01-04')
  })

  it('handles a leap-day week', () => {
    expect(weekEndFor('2024-02-26')).toBe('2024-03-03')
  })
})

describe('existingWeeklyReportId', () => {
  it('extracts the id from a 40903 duplicate-week error', () => {
    const error = new ApiError(40903, '该自然周周报已存在', 409, {
      existing_weekly_report_id: '01AAA'
    })
    expect(existingWeeklyReportId(error)).toBe('01AAA')
  })

  it('returns null for an unrelated error', () => {
    expect(existingWeeklyReportId(new ApiError(40401, 'x', 404, {}))).toBeNull()
  })

  it('returns null for a non-ApiError value', () => {
    expect(existingWeeklyReportId(new Error('boom'))).toBeNull()
  })
})

describe('formatWeeklyFieldValue', () => {
  it('renders null as an em dash', () => {
    expect(formatWeeklyFieldValue(null)).toBe('—')
  })

  it('joins a multiselect array with a Chinese enumeration comma', () => {
    expect(formatWeeklyFieldValue(['开发', '评审'])).toBe('开发、评审')
  })

  it('renders an empty array as an em dash', () => {
    expect(formatWeeklyFieldValue([])).toBe('—')
  })

  it('stringifies a number', () => {
    expect(formatWeeklyFieldValue(2.5)).toBe('2.5')
  })

  it('passes a plain string through unchanged', () => {
    expect(formatWeeklyFieldValue('完成开发')).toBe('完成开发')
  })

  it('formats a PROJECT_LIST source value as project/content pairs, omitting blank fields', () => {
    expect(
      formatWeeklyFieldValue([
        {
          category: '重要',
          project: '个人日报系统',
          content: '完成Excel导出功能',
          weight: '50%',
          planned_completion_date: '',
          actual_completion_date: '',
          owner: '张三',
          assistant: '',
          required_resources: '',
          completion_notes: ''
        },
        {
          category: '一般',
          project: '能源管理平台',
          content: '设计设备接口',
          weight: '',
          planned_completion_date: '',
          actual_completion_date: '',
          owner: '',
          assistant: '',
          required_resources: '',
          completion_notes: ''
        }
      ])
    ).toBe(
      '类别：重要，个人日报系统：完成Excel导出功能，权重：50%，责任人：张三；' +
        '类别：一般，能源管理平台：设计设备接口'
    )
  })
})

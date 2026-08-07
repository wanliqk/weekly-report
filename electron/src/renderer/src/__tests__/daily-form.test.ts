import { describe, expect, it } from 'vitest'

import { ApiError } from '@renderer/api/client'
import type { TemplateFieldData } from '@renderer/types/template'
import {
  dailyFieldErrors,
  dailyStatusLabel,
  formatDailyFieldValue,
  formatShanghaiTime,
  generateClientRequestId,
  initializeDailyContent,
  todayInShanghai
} from '@renderer/utils/daily-form'

const fields: TemplateFieldData[] = [
  {
    field_key: 'text-key',
    label: '工作内容',
    description: '',
    field_type: 'textarea',
    required: true,
    enabled: true,
    sort_order: 0,
    options: [],
    core_type: 'today_work'
  },
  {
    field_key: 'multi-key',
    label: '标签',
    description: '',
    field_type: 'multiselect',
    required: false,
    enabled: true,
    sort_order: 1,
    options: ['A', 'B'],
    core_type: null
  },
  {
    field_key: 'disabled-key',
    label: '停用字段',
    description: '',
    field_type: 'text',
    required: false,
    enabled: false,
    sort_order: 2,
    options: [],
    core_type: null
  }
]

describe('daily form helpers', () => {
  it('builds editable content only from enabled snapshot fields', () => {
    const originalTags = ['A']
    const content = initializeDailyContent(fields, {
      'text-key': '完成接口',
      'multi-key': originalTags,
      'disabled-key': '不可见'
    })

    expect(content).toEqual({ 'text-key': '完成接口', 'multi-key': ['A'] })
    expect(content['multi-key']).not.toBe(originalTags)
  })

  it('maps business validation errors back to their fields', () => {
    const error = new ApiError(42201, '校验失败', 422, {
      errors: [{ field: 'text-key', message: '必填字段不能为空' }]
    })

    expect(dailyFieldErrors(error)).toEqual({ 'text-key': '必填字段不能为空' })
  })

  it('formats statuses and creates an ISO date in the fixed timezone', () => {
    expect(dailyStatusLabel('archived')).toBe('已归档')
    expect(todayInShanghai()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(formatShanghaiTime('2026-08-05T08:00:00+00:00')).toContain('16:00:00')
    expect(formatShanghaiTime(null)).toBe('—')
  })

  it('generates a fresh client request id on every call', () => {
    const first = generateClientRequestId()
    const second = generateClientRequestId()
    expect(first).not.toBe(second)
    expect(first).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('formats a daily field value for read-only display', () => {
    expect(formatDailyFieldValue(null)).toBe('—')
    expect(formatDailyFieldValue([])).toBe('—')
    expect(formatDailyFieldValue(['开发', '评审'])).toBe('开发、评审')
    expect(formatDailyFieldValue(2.5)).toBe('2.5')
    expect(formatDailyFieldValue('完成开发')).toBe('完成开发')
  })
})

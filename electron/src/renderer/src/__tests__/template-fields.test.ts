import { describe, expect, it } from 'vitest'

import type { TemplateFieldData } from '@renderer/types/template'
import {
  createTemplateFieldDraft,
  emptyFieldValue,
  formatProjectListEntries,
  isProjectListArray,
  projectTaskStatusLabel,
  toTemplateFieldDrafts,
  toTemplateFieldPayload,
  usesOptions,
  validateTemplateFields
} from '@renderer/utils/template-fields'

const coreFields: TemplateFieldData[] = [
  {
    field_key: '01J00000000000000000000001',
    label: '今日工作',
    description: '',
    field_type: 'textarea',
    required: true,
    enabled: true,
    sort_order: 0,
    options: [],
    core_type: 'today_work'
  },
  {
    field_key: '01J00000000000000000000002',
    label: '明日计划',
    description: '',
    field_type: 'textarea',
    required: false,
    enabled: true,
    sort_order: 1,
    options: [],
    core_type: 'tomorrow_plan'
  }
]

describe('template field helpers', () => {
  it('keeps existing stable keys and omits a key for new fields', () => {
    const drafts = toTemplateFieldDrafts(coreFields)
    const custom = createTemplateFieldDraft()
    custom.label = '工时'
    custom.field_type = 'number'
    drafts.push(custom)

    const payload = toTemplateFieldPayload(drafts)

    expect(payload[0]?.field_key).toBe(coreFields[0]?.field_key)
    expect(payload[2]).not.toHaveProperty('field_key')
    expect(payload.map((field) => field.sort_order)).toEqual([0, 1, 2])
  })

  it('rejects duplicate select options and disabling both core fields', () => {
    const drafts = toTemplateFieldDrafts(coreFields)
    drafts.forEach((field) => {
      field.enabled = false
    })
    const select = createTemplateFieldDraft()
    select.label = '环境'
    select.field_type = 'select'
    select.options = ['生产', '生产']
    drafts.push(select)

    expect(validateTemplateFields(drafts)).toEqual(
      expect.arrayContaining(['环境：选项不能重复', '“今日工作”与“明日计划”至少启用一个'])
    )
  })

  it('treats PROJECT_LIST like multiselect for options and empty-value defaults', () => {
    expect(usesOptions('PROJECT_LIST')).toBe(false)
    expect(emptyFieldValue('PROJECT_LIST')).toEqual([])
    expect(emptyFieldValue('multiselect')).toEqual([])
    expect(emptyFieldValue('number')).toBeNull()
    expect(emptyFieldValue('text')).toBe('')
  })

  it('distinguishes project-list arrays from multiselect string arrays', () => {
    expect(isProjectListArray([])).toBe(true)
    expect(isProjectListArray(['开发', '评审'])).toBe(false)
    expect(
      isProjectListArray([{ project: '个人日报系统', content: '完成导出', status: 'DONE' }])
    ).toBe(true)
  })

  it('labels project task statuses and formats entries for read-only display', () => {
    expect(projectTaskStatusLabel('TODO')).toBe('未开始')
    expect(projectTaskStatusLabel('DOING')).toBe('进行中')
    expect(projectTaskStatusLabel('DONE')).toBe('已完成')

    const entries = [
      { project: '个人日报系统', content: '完成Excel导出功能', status: 'DONE' as const },
      { project: '能源管理平台', content: '设计设备接口', status: 'DOING' as const }
    ]
    expect(formatProjectListEntries(entries)).toBe(
      '个人日报系统：完成Excel导出功能（已完成）；能源管理平台：设计设备接口（进行中）'
    )
  })
})

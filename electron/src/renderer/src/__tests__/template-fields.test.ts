import { describe, expect, it } from 'vitest'

import type { TemplateFieldData } from '@renderer/types/template'
import {
  createTemplateFieldDraft,
  emptyFieldValue,
  emptyProjectListEntry,
  formatProjectListEntries,
  isBlankProjectListEntry,
  isProjectListArray,
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
    show_in_export: true,
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
    show_in_export: true,
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

  it('defaults show_in_export to true for new fields and lets it be toggled off', () => {
    const draft = createTemplateFieldDraft()
    expect(draft.show_in_export).toBe(true)

    draft.label = '内部备注'
    draft.show_in_export = false
    const payload = toTemplateFieldPayload([...toTemplateFieldDrafts(coreFields), draft])

    expect(payload[0]?.show_in_export).toBe(true)
    expect(payload[2]?.show_in_export).toBe(false)
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

  it('treats an untouched default-category project row as blank', () => {
    expect(isBlankProjectListEntry(emptyProjectListEntry())).toBe(true)
    expect(isBlankProjectListEntry({ ...emptyProjectListEntry(), project: '  ' })).toBe(true)
    expect(isBlankProjectListEntry({ ...emptyProjectListEntry(), category: '一般' })).toBe(false)
    expect(isBlankProjectListEntry({ ...emptyProjectListEntry(), weight: '30%' })).toBe(false)
    expect(isBlankProjectListEntry({ ...emptyProjectListEntry(), project: '个人日报系统' })).toBe(
      false
    )
  })

  it('distinguishes project-list arrays from multiselect string arrays', () => {
    expect(isProjectListArray([])).toBe(true)
    expect(isProjectListArray(['开发', '评审'])).toBe(false)
    expect(
      isProjectListArray([
        {
          category: '重要',
          project: '个人日报系统',
          content: '完成导出',
          weight: '',
          planned_completion_date: '',
          actual_completion_date: '',
          owner: '',
          assistant: '',
          required_resources: '',
          completion_notes: ''
        }
      ])
    ).toBe(true)
  })

  it('formats project-list entries for read-only display, omitting blank optional fields', () => {
    const entries = [
      {
        category: '重要',
        project: '个人日报系统',
        content: '完成Excel导出功能',
        weight: '',
        planned_completion_date: '',
        actual_completion_date: '',
        owner: '',
        assistant: '',
        required_resources: '',
        completion_notes: ''
      },
      {
        category: '一般',
        project: '能源管理平台',
        content: '设计设备接口',
        weight: '30%',
        planned_completion_date: '2026-08-20',
        actual_completion_date: '',
        owner: '张三',
        assistant: '李四',
        required_resources: '',
        completion_notes: ''
      }
    ]
    expect(formatProjectListEntries(entries)).toBe(
      '类别：重要，个人日报系统：完成Excel导出功能；' +
        '类别：一般，能源管理平台：设计设备接口，权重：30%，预计完成：2026-08-20，责任人：张三，协助人：李四'
    )
  })
})

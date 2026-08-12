import type { DailyFieldValue, ProjectListEntry } from '../types/daily-report'
import type {
  TemplateCoreType,
  TemplateFieldData,
  TemplateFieldInput,
  TemplateFieldType
} from '../types/template'

let draftSequence = 0

export function isProjectListArray(value: unknown[]): value is ProjectListEntry[] {
  return value.every(
    (item) => typeof item === 'object' && item !== null && 'project' in item && 'content' in item
  )
}

// Optional tracking fields that follow the `project`/`content` pair in the
// read-only summary. `category` is prepended separately because its column
// appears before `project`; empty values are omitted.
const PROJECT_LIST_TRAILING_FIELD_LABELS: [keyof ProjectListEntry, string][] = [
  ['weight', '权重'],
  ['planned_completion_date', '预计完成'],
  ['actual_completion_date', '实际完成'],
  ['owner', '责任人'],
  ['assistant', '协助人'],
  ['required_resources', '所需资源支持'],
  ['completion_notes', '完成情况及解决措施']
]

export function formatProjectListEntries(entries: ProjectListEntry[]): string {
  return entries.map(formatProjectListEntry).join('；')
}

function formatProjectListEntry(entry: ProjectListEntry): string {
  const segments = [
    ...(entry.category.trim() === '' ? [] : [`类别：${entry.category}`]),
    `${entry.project}：${entry.content}`,
    ...PROJECT_LIST_TRAILING_FIELD_LABELS.filter(([key]) => entry[key].trim() !== '').map(
      ([key, label]) => `${label}：${entry[key]}`
    )
  ]
  return segments.join('，')
}

export interface TemplateFieldDraft {
  client_key: string
  field_key?: string
  label: string
  description: string
  field_type: TemplateFieldType
  required: boolean
  enabled: boolean
  show_in_export: boolean
  options: string[]
  core_type: TemplateCoreType | null
}

export function toTemplateFieldDrafts(fields: TemplateFieldData[]): TemplateFieldDraft[] {
  return [...fields]
    .sort((left, right) => left.sort_order - right.sort_order)
    .map((field) => ({
      client_key: field.field_key,
      field_key: field.field_key,
      label: field.label,
      description: field.description,
      field_type: field.field_type,
      required: field.required,
      enabled: field.enabled,
      show_in_export: field.show_in_export,
      options: [...field.options],
      core_type: field.core_type
    }))
}

export function createTemplateFieldDraft(): TemplateFieldDraft {
  draftSequence += 1
  return {
    client_key: `new-${draftSequence}`,
    label: '',
    description: '',
    field_type: 'text',
    required: false,
    enabled: true,
    show_in_export: true,
    options: [],
    core_type: null
  }
}

export function toTemplateFieldPayload(fields: TemplateFieldDraft[]): TemplateFieldInput[] {
  return fields.map((field, index) => {
    const input: TemplateFieldInput = {
      label: field.label.trim(),
      description: field.description.trim(),
      field_type: field.field_type,
      required: field.required,
      enabled: field.enabled,
      show_in_export: field.show_in_export,
      sort_order: index,
      options: usesOptions(field.field_type)
        ? field.options.map((option) => option.trim()).filter(Boolean)
        : []
    }
    if (field.field_key) {
      input.field_key = field.field_key
    }
    return input
  })
}

export function validateTemplateFields(fields: TemplateFieldDraft[]): string[] {
  const errors: string[] = []
  if (fields.length === 0) {
    errors.push('模板至少需要一个字段')
  }
  fields.forEach((field, index) => {
    const displayName = field.label.trim() || `第 ${index + 1} 个字段`
    if (!field.label.trim()) {
      errors.push(`${displayName}：名称不能为空`)
    }
    if (usesOptions(field.field_type)) {
      const options = field.options.map((option) => option.trim()).filter(Boolean)
      if (options.length === 0) {
        errors.push(`${displayName}：至少需要一个选项`)
      }
      const normalized = options.map((option) => option.toLocaleLowerCase())
      if (new Set(normalized).size !== normalized.length) {
        errors.push(`${displayName}：选项不能重复`)
      }
    }
  })
  if (!fields.some((field) => field.core_type !== null && field.enabled)) {
    errors.push('“今日工作”与“明日计划”至少启用一个')
  }
  return errors
}

export function usesOptions(fieldType: TemplateFieldType): boolean {
  return fieldType === 'select' || fieldType === 'multiselect'
}

export function emptyProjectListEntry(): ProjectListEntry {
  return {
    category: '重要',
    project: '',
    content: '',
    weight: '',
    planned_completion_date: '',
    actual_completion_date: '',
    owner: '',
    assistant: '',
    required_resources: '',
    completion_notes: ''
  }
}

export function isBlankProjectListEntry(entry: ProjectListEntry): boolean {
  return (
    entry.category.trim() === '重要' &&
    Object.entries(entry).every(([key, value]) => key === 'category' || value.trim() === '')
  )
}

export function emptyFieldValue(fieldType: TemplateFieldType): DailyFieldValue {
  if (fieldType === 'multiselect' || fieldType === 'PROJECT_LIST') {
    return []
  }
  if (fieldType === 'number') {
    return null
  }
  return ''
}

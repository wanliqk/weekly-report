import type { DailyFieldValue, ProjectListEntry, ProjectTaskStatus } from '../types/daily-report'
import type {
  TemplateCoreType,
  TemplateFieldData,
  TemplateFieldInput,
  TemplateFieldType
} from '../types/template'

let draftSequence = 0

const PROJECT_TASK_STATUS_LABELS: Record<ProjectTaskStatus, string> = {
  TODO: '未开始',
  DOING: '进行中',
  DONE: '已完成'
}

export function projectTaskStatusLabel(status: ProjectTaskStatus): string {
  return PROJECT_TASK_STATUS_LABELS[status]
}

export function isProjectListArray(value: unknown[]): value is ProjectListEntry[] {
  return value.every(
    (item) => typeof item === 'object' && item !== null && 'project' in item && 'content' in item
  )
}

export function formatProjectListEntries(entries: ProjectListEntry[]): string {
  return entries
    .map((entry) => `${entry.project}：${entry.content}（${projectTaskStatusLabel(entry.status)}）`)
    .join('；')
}

export interface TemplateFieldDraft {
  client_key: string
  field_key?: string
  label: string
  description: string
  field_type: TemplateFieldType
  required: boolean
  enabled: boolean
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

export function emptyFieldValue(fieldType: TemplateFieldType): DailyFieldValue {
  if (fieldType === 'multiselect' || fieldType === 'PROJECT_LIST') {
    return []
  }
  if (fieldType === 'number') {
    return null
  }
  return ''
}

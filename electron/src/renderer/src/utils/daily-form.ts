import { ApiError } from '../api/client'
import type { DailyContent, DailyFieldValue, DailyStatus } from '../types/daily-report'
import type { TemplateFieldData } from '../types/template'
import { emptyFieldValue } from './template-fields'

interface FieldErrorData {
  errors: Array<{ field: string; message: string }>
}

export function initializeDailyContent(
  fields: TemplateFieldData[],
  source: DailyContent
): DailyContent {
  return Object.fromEntries(
    fields
      .filter((field) => field.enabled)
      .sort((left, right) => left.sort_order - right.sort_order)
      .map((field) => [
        field.field_key,
        field.field_key in source
          ? cloneDailyValue(source[field.field_key])
          : emptyFieldValue(field.field_type)
      ])
  )
}

export function dailyFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.code !== 42201 || !isFieldErrorData(error.data)) {
    return {}
  }
  return Object.fromEntries(error.data.errors.map((item) => [item.field, item.message]))
}

export function dailyStatusLabel(status: DailyStatus): string {
  return { draft: '草稿', submitted: '已提交', archived: '已归档' }[status]
}

export function todayInShanghai(): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(new Date())
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day}`
}

export function formatShanghaiTime(value: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function cloneDailyValue(value: DailyFieldValue | undefined): DailyFieldValue {
  return Array.isArray(value) ? [...value] : (value ?? null)
}

function isFieldErrorData(value: unknown): value is FieldErrorData {
  if (typeof value !== 'object' || value === null || !('errors' in value)) {
    return false
  }
  const errors = value.errors
  return (
    Array.isArray(errors) &&
    errors.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        'field' in item &&
        typeof item.field === 'string' &&
        'message' in item &&
        typeof item.message === 'string'
    )
  )
}

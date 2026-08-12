import { ApiError } from '../api/client'
import type { DailyContent, DailyFieldValue, DailyStatus } from '../types/daily-report'
import type { TemplateFieldData } from '../types/template'
import {
  emptyFieldValue,
  emptyProjectListEntry,
  formatProjectListEntries,
  isBlankProjectListEntry,
  isProjectListArray
} from './template-fields'

interface FieldErrorData {
  errors: Array<{ field: string; message: string }>
}

/**
 * A `PROJECT_LIST` field with no rows initializes with one editable default
 * row instead of the empty-state placeholder, so the user can start typing
 * without an extra "add project" click. `sanitizeDailyContent` strips an
 * untouched default row back out before the content is sent to the backend,
 * so its non-empty defaults never trip required-field or entry validation.
 */
export function initializeDailyContent(
  fields: TemplateFieldData[],
  source: DailyContent,
  defaultProjectOwner = ''
): DailyContent {
  return Object.fromEntries(
    fields
      .filter((field) => field.enabled)
      .sort((left, right) => left.sort_order - right.sort_order)
      .map((field) => [field.field_key, initialFieldValue(field, source, defaultProjectOwner)])
  )
}

function initialFieldValue(
  field: TemplateFieldData,
  source: DailyContent,
  defaultProjectOwner: string
): DailyFieldValue {
  const value =
    field.field_key in source
      ? cloneDailyValue(source[field.field_key])
      : emptyFieldValue(field.field_type)
  if (field.field_type === 'PROJECT_LIST' && Array.isArray(value) && value.length === 0) {
    return [emptyProjectListEntry(defaultProjectOwner)]
  }
  return value
}

export function sanitizeDailyContent(
  fields: TemplateFieldData[],
  content: DailyContent,
  defaultProjectOwner = ''
): DailyContent {
  const fieldTypeByKey = new Map(fields.map((field) => [field.field_key, field.field_type]))
  return Object.fromEntries(
    Object.entries(content).map(([key, value]) => {
      const isProjectList =
        fieldTypeByKey.get(key) === 'PROJECT_LIST' &&
        Array.isArray(value) &&
        isProjectListArray(value)
      return [
        key,
        isProjectList
          ? value.filter((entry) => !isBlankProjectListEntry(entry, defaultProjectOwner))
          : value
      ]
    })
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

/** One `client_request_id` per creation intent (`docs/方案设计.md` §6.2): generated once when the user starts creating an entry, then reused across retries of that same intent so a network retry never produces a duplicate entry. */
export function generateClientRequestId(): string {
  return crypto.randomUUID()
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

export function formatDailyFieldValue(value: DailyFieldValue): string {
  if (value === null) {
    return '—'
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '—'
    }
    return isProjectListArray(value) ? formatProjectListEntries(value) : value.join('、')
  }
  return String(value)
}

function cloneDailyValue(value: DailyFieldValue | undefined): DailyFieldValue {
  if (!Array.isArray(value)) {
    return value ?? null
  }
  return isProjectListArray(value) ? value.map((item) => ({ ...item })) : [...value]
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

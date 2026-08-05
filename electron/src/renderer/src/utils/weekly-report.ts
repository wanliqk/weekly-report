import { ApiError } from '../api/client'
import { todayInShanghai } from './daily-form'

const MULTISELECT_SEPARATOR = '、'

/** Parses a `YYYY-MM-DD` calendar date into a UTC-anchored `Date` used purely for date arithmetic (never for real moments/timezones). */
function toCalendarDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day))
}

function toDateString(date: Date): string {
  return date.toISOString().slice(0, 10)
}

export function mondayOfWeek(value: string): string {
  const date = toCalendarDate(value)
  const weekday = date.getUTCDay() // 0 = Sunday .. 6 = Saturday
  const diffToMonday = weekday === 0 ? 6 : weekday - 1
  date.setUTCDate(date.getUTCDate() - diffToMonday)
  return toDateString(date)
}

export function weekEndFor(weekStart: string): string {
  const date = toCalendarDate(weekStart)
  date.setUTCDate(date.getUTCDate() + 6)
  return toDateString(date)
}

export function currentWeekStart(): string {
  return mondayOfWeek(todayInShanghai())
}

export function existingWeeklyReportId(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.code !== 40903) {
    return null
  }
  const data = error.data as { existing_weekly_report_id?: unknown }
  return typeof data.existing_weekly_report_id === 'string' ? data.existing_weekly_report_id : null
}

export function formatWeeklyFieldValue(value: string | number | string[] | null): string {
  if (value === null) {
    return '—'
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(MULTISELECT_SEPARATOR) : '—'
  }
  return String(value)
}

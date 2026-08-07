import type { DailyDayCellStatus, DailyReportDayMonthItemData } from '../types/daily-report-day'

type DayCellStatusInput = Pick<
  DailyReportDayMonthItemData,
  'status' | 'draft_count' | 'submitted_count'
>

/** Derives the calendar-cell status text/tag from a month-summary row or day-detail payload (`docs/方案设计.md` §8.3): `undefined` means the date has no `daily_report_days` row at all. */
export function dayCellStatus(item: DayCellStatusInput | undefined): DailyDayCellStatus {
  if (!item) {
    return 'none'
  }
  if (item.status === 'archived') {
    return 'archived'
  }
  if (item.draft_count > 0 && item.submitted_count > 0) {
    return 'mixed'
  }
  if (item.draft_count > 0) {
    return 'draft'
  }
  if (item.submitted_count > 0) {
    return 'submitted'
  }
  return 'none'
}

export function dayCellStatusLabel(status: DailyDayCellStatus): string {
  return {
    none: '无记录',
    draft: '草稿',
    submitted: '待归档',
    mixed: '草稿+待归档',
    archived: '已完成'
  }[status]
}

export function dayCellStatusTagType(
  status: DailyDayCellStatus
): 'info' | 'warning' | 'success' | 'primary' {
  return {
    none: 'info' as const,
    draft: 'warning' as const,
    submitted: 'primary' as const,
    mixed: 'warning' as const,
    archived: 'success' as const
  }[status]
}

export function currentMonthInShanghai(): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit'
  }).formatToParts(new Date())
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${value.year}-${value.month}`
}

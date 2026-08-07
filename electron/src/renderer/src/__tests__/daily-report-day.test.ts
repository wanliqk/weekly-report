import { describe, expect, it } from 'vitest'

import type { DailyReportDayMonthItemData } from '@renderer/types/daily-report-day'
import {
  currentMonthInShanghai,
  dayCellStatus,
  dayCellStatusLabel,
  dayCellStatusTagType
} from '@renderer/utils/daily-report-day'

function item(overrides: Partial<DailyReportDayMonthItemData>): DailyReportDayMonthItemData {
  return {
    work_date: '2026-08-07',
    day_id: '01AAA',
    status: 'open',
    draft_count: 0,
    submitted_count: 0,
    archived_count: 0,
    total_count: 0,
    can_create: true,
    can_archive: false,
    archive_disabled_reason: '尚无已提交条目',
    ...overrides
  }
}

describe('dayCellStatus', () => {
  it('is none when no row exists for the date', () => {
    expect(dayCellStatus(undefined)).toBe('none')
  })

  it('is archived once the day container is archived', () => {
    expect(dayCellStatus(item({ status: 'archived', archived_count: 2, total_count: 2 }))).toBe(
      'archived'
    )
  })

  it('is draft when only drafts exist', () => {
    expect(dayCellStatus(item({ draft_count: 1 }))).toBe('draft')
  })

  it('is submitted when only submitted entries exist', () => {
    expect(dayCellStatus(item({ submitted_count: 2 }))).toBe('submitted')
  })

  it('is mixed when drafts and submitted entries coexist', () => {
    expect(dayCellStatus(item({ draft_count: 1, submitted_count: 1 }))).toBe('mixed')
  })
})

describe('dayCellStatusLabel / dayCellStatusTagType', () => {
  it('gives every status a non-color-only text label', () => {
    for (const status of ['none', 'draft', 'submitted', 'mixed', 'archived'] as const) {
      expect(dayCellStatusLabel(status)).not.toBe('')
      expect(dayCellStatusTagType(status)).not.toBe('')
    }
  })
})

describe('currentMonthInShanghai', () => {
  it('returns a YYYY-MM string', () => {
    expect(currentMonthInShanghai()).toMatch(/^\d{4}-\d{2}$/)
  })
})

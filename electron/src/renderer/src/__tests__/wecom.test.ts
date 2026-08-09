import { describe, expect, it } from 'vitest'

import type { TemplateFieldData } from '@renderer/types/template'
import type {
  WeComFieldMappingRule,
  WeComSyncRecordData,
  WeComSyncStatus
} from '@renderer/types/wecom'
import {
  parseWeComFormId,
  replaceVisibleWeComFieldMappingRules,
  upsertWeComFieldMappingRule,
  weComFieldMappingRuleTarget,
  weComMappableTemplateFields,
  weComSyncActionLabel,
  weComSyncIsRetryEligible,
  weComSyncStatusLabel,
  weComSyncStatusTagType,
  weComSyncSummary
} from '@renderer/utils/wecom'

describe('parseWeComFormId', () => {
  it('passes a raw form id through unchanged', () => {
    expect(parseWeComFormId('AKUAmwcxAA4AMcALQaMABgCNxhNl1H9Mj_fork')).toBe(
      'AKUAmwcxAA4AMcALQaMABgCNxhNl1H9Mj_fork'
    )
  })

  it('trims surrounding whitespace on a raw id', () => {
    expect(parseWeComFormId('  form-123  ')).toBe('form-123')
  })

  it('extracts the id segment from a full form link with a query string', () => {
    expect(
      parseWeComFormId('https://doc.weixin.qq.com/forms/j/AAAA-bbbb_1234?page=5&_cef_tabid_=abc')
    ).toBe('AAAA-bbbb_1234')
  })

  it('extracts the id segment from a full form link with a fragment', () => {
    expect(
      parseWeComFormId(
        'https://doc.weixin.qq.com/forms/j/AAAA-bbbb_1234#/journal-answer/8?journaluuid=xyz'
      )
    ).toBe('AAAA-bbbb_1234')
  })

  it('extracts the id segment when the link has neither query nor fragment', () => {
    expect(parseWeComFormId('https://doc.weixin.qq.com/forms/j/AAAA-bbbb_1234')).toBe(
      'AAAA-bbbb_1234'
    )
  })

  it('extracts the id segment when a trailing path segment follows the id', () => {
    expect(parseWeComFormId('https://doc.weixin.qq.com/forms/j/AAAA-bbbb_1234/preview')).toBe(
      'AAAA-bbbb_1234'
    )
  })

  it('returns null for blank input', () => {
    expect(parseWeComFormId('   ')).toBeNull()
    expect(parseWeComFormId('')).toBeNull()
  })

  it('returns null when the extracted id would be empty', () => {
    expect(parseWeComFormId('https://doc.weixin.qq.com/forms/j/?page=5')).toBeNull()
  })

  it('returns null for an id longer than 128 characters', () => {
    expect(parseWeComFormId('x'.repeat(129))).toBeNull()
  })

  it('accepts an id of exactly 128 characters', () => {
    const id = 'x'.repeat(128)
    expect(parseWeComFormId(id)).toBe(id)
  })
})

const ALL_STATUSES: WeComSyncStatus[] = [
  'pending',
  'syncing',
  'succeeded',
  'failed',
  'auth_required',
  'schema_changed',
  'duplicate_detected',
  'uncertain'
]

describe('weComSyncStatusLabel / weComSyncStatusTagType', () => {
  it.each(ALL_STATUSES)('has a non-empty Chinese label for %s', (status) => {
    expect(weComSyncStatusLabel(status).length).toBeGreaterThan(0)
  })

  it.each(ALL_STATUSES)('has a tag type for %s', (status) => {
    expect(['success', 'warning', 'danger', 'info']).toContain(weComSyncStatusTagType(status))
  })

  it('maps succeeded to success and failure-ish states to danger/warning', () => {
    expect(weComSyncStatusTagType('succeeded')).toBe('success')
    expect(weComSyncStatusTagType('failed')).toBe('danger')
    expect(weComSyncStatusTagType('auth_required')).toBe('danger')
    expect(weComSyncStatusTagType('schema_changed')).toBe('danger')
  })
})

describe('weComSyncIsRetryEligible / weComSyncActionLabel', () => {
  it('allows retry only for failed/auth_required/schema_changed/duplicate_detected', () => {
    expect(weComSyncIsRetryEligible('failed')).toBe(true)
    expect(weComSyncIsRetryEligible('auth_required')).toBe(true)
    expect(weComSyncIsRetryEligible('schema_changed')).toBe(true)
    expect(weComSyncIsRetryEligible('duplicate_detected')).toBe(true)
    expect(weComSyncIsRetryEligible('uncertain')).toBe(false)
    expect(weComSyncIsRetryEligible('pending')).toBe(false)
    expect(weComSyncIsRetryEligible('syncing')).toBe(false)
    expect(weComSyncIsRetryEligible('succeeded')).toBe(false)
  })

  it('returns 同步 for a fresh pending record', () => {
    expect(weComSyncActionLabel('pending')).toBe('同步')
  })

  it('returns 重试 only for a directly retryable failure in history UI', () => {
    expect(weComSyncActionLabel('failed')).toBe('重试')
    expect(weComSyncActionLabel('duplicate_detected')).toBeNull()
    expect(weComSyncActionLabel('auth_required')).toBeNull()
    expect(weComSyncActionLabel('schema_changed')).toBeNull()
  })

  it('returns null when no action currently applies', () => {
    expect(weComSyncActionLabel('syncing')).toBeNull()
    expect(weComSyncActionLabel('succeeded')).toBeNull()
    expect(weComSyncActionLabel('uncertain')).toBeNull()
  })
})

function record(overrides: Partial<WeComSyncRecordData> = {}): WeComSyncRecordData {
  return {
    id: '01ARZ3NDEKTSV4RRFFQ69G5FAV',
    daily_report_day_id: '01ARZ3NDEKTSV4RRFFQ69G5FAW',
    work_date: '2026-08-09',
    destination_fingerprint: 'a'.repeat(64),
    status: 'pending',
    attempt_count: 0,
    remote_answer_id: null,
    remote_reply_id: null,
    remote_journal_uuid: null,
    last_error_kind: null,
    last_error_message: null,
    last_attempt_at: null,
    succeeded_at: null,
    created_at: '2026-08-09T00:00:00+00:00',
    updated_at: '2026-08-09T00:00:00+00:00',
    ...overrides
  }
}

describe('weComSyncSummary', () => {
  it('prefers the server-provided error message when present', () => {
    expect(
      weComSyncSummary(record({ status: 'failed', last_error_message: '企业微信拒绝了本次提交' }))
    ).toBe('企业微信拒绝了本次提交')
  })

  it('reports a fixed success sentence for a succeeded record without an error message', () => {
    expect(weComSyncSummary(record({ status: 'succeeded' }))).toBe('已成功同步到企业微信')
  })

  it('falls back to the status label when there is no error message', () => {
    expect(weComSyncSummary(record({ status: 'pending' }))).toBe('待同步')
  })
})

function field(overrides: Partial<TemplateFieldData>): TemplateFieldData {
  return {
    field_key: '01AAAAAAAAAAAAAAAAAAAAAAAA',
    label: '字段',
    description: '',
    field_type: 'text',
    required: false,
    enabled: true,
    sort_order: 0,
    options: [],
    core_type: null,
    ...overrides
  }
}

describe('weComMappableTemplateFields', () => {
  it('excludes core fields, PROJECT_LIST fields, and disabled fields', () => {
    const fields: TemplateFieldData[] = [
      field({ field_key: 'today', core_type: 'today_work', sort_order: 0 }),
      field({ field_key: 'tomorrow', core_type: 'tomorrow_plan', sort_order: 1 }),
      field({ field_key: 'projects', field_type: 'PROJECT_LIST', sort_order: 2 }),
      field({ field_key: 'disabled-custom', enabled: false, sort_order: 3 }),
      field({ field_key: 'owner', label: '责任人', sort_order: 4 }),
      field({ field_key: 'notes', label: '备注', field_type: 'textarea', sort_order: 5 })
    ]

    const mappable = weComMappableTemplateFields(fields)

    expect(mappable.map((item) => item.field_key)).toEqual(['owner', 'notes'])
  })

  it('sorts by sort_order regardless of input order', () => {
    const fields: TemplateFieldData[] = [
      field({ field_key: 'b', sort_order: 5 }),
      field({ field_key: 'a', sort_order: 1 })
    ]

    expect(weComMappableTemplateFields(fields).map((item) => item.field_key)).toEqual(['a', 'b'])
  })
})

describe('weComFieldMappingRuleTarget / upsertWeComFieldMappingRule', () => {
  it('returns null when no rule exists for the field', () => {
    expect(weComFieldMappingRuleTarget([], 'owner')).toBeNull()
  })

  it('finds the target for an existing rule', () => {
    const rules: WeComFieldMappingRule[] = [{ field_key: 'owner', target: 'today_work' }]
    expect(weComFieldMappingRuleTarget(rules, 'owner')).toBe('today_work')
  })

  it('adds a new rule when none existed', () => {
    const result = upsertWeComFieldMappingRule([], 'owner', 'today_work')
    expect(result).toEqual([{ field_key: 'owner', target: 'today_work' }])
  })

  it('replaces an existing rule for the same field without duplicating it', () => {
    const rules: WeComFieldMappingRule[] = [{ field_key: 'owner', target: 'today_work' }]
    const result = upsertWeComFieldMappingRule(rules, 'owner', 'tomorrow_plan')
    expect(result).toEqual([{ field_key: 'owner', target: 'tomorrow_plan' }])
  })

  it('removes the rule when target is null', () => {
    const rules: WeComFieldMappingRule[] = [
      { field_key: 'owner', target: 'today_work' },
      { field_key: 'notes', target: 'ignore' }
    ]
    const result = upsertWeComFieldMappingRule(rules, 'owner', null)
    expect(result).toEqual([{ field_key: 'notes', target: 'ignore' }])
  })

  it('does not mutate the input array', () => {
    const rules: WeComFieldMappingRule[] = [{ field_key: 'owner', target: 'today_work' }]
    upsertWeComFieldMappingRule(rules, 'notes', 'ignore')
    expect(rules).toEqual([{ field_key: 'owner', target: 'today_work' }])
  })

  it('leaves other fields untouched', () => {
    const rules: WeComFieldMappingRule[] = [
      { field_key: 'owner', target: 'today_work' },
      { field_key: 'notes', target: 'ignore' }
    ]
    const result = upsertWeComFieldMappingRule(rules, 'owner', 'ignore')
    expect(result).toEqual(
      expect.arrayContaining([
        { field_key: 'owner', target: 'ignore' },
        { field_key: 'notes', target: 'ignore' }
      ])
    )
    expect(result).toHaveLength(2)
  })
})

describe('replaceVisibleWeComFieldMappingRules', () => {
  it('replaces current-template rules while preserving historical field mappings', () => {
    const result = replaceVisibleWeComFieldMappingRules(
      [
        { field_key: 'current-owner', target: 'today_work' },
        { field_key: 'historical-notes', target: 'tomorrow_plan' }
      ],
      ['current-owner', 'current-risk'],
      { 'current-owner': 'ignore', 'current-risk': 'today_work' }
    )

    expect(result).toEqual([
      { field_key: 'historical-notes', target: 'tomorrow_plan' },
      { field_key: 'current-owner', target: 'ignore' },
      { field_key: 'current-risk', target: 'today_work' }
    ])
  })

  it('removes a visible rule set back to unmapped without touching hidden rules', () => {
    const result = replaceVisibleWeComFieldMappingRules(
      [
        { field_key: 'visible', target: 'today_work' },
        { field_key: 'historical', target: 'ignore' }
      ],
      ['visible'],
      { visible: 'unmapped' }
    )

    expect(result).toEqual([{ field_key: 'historical', target: 'ignore' }])
  })
})

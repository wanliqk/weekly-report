import type { TemplateFieldData } from '../types/template'
import type {
  WeComFieldMappingRule,
  WeComFieldMappingTarget,
  WeComSyncRecordData,
  WeComSyncStatus
} from '../types/wecom'

const MAX_FORM_ID_LENGTH = 128
// `wx-ribao.py` (the user-provided reference script analyzed during WECOM-01,
// see `ai-docs/task.md`'s WECOM-06 record) resolves its form id as
// `url.split('/forms/j/')[1].split('?')[0]` from a link shaped like
// `https://doc.weixin.qq.com/forms/j/<id>?page=...#/journal-answer/...`.
const FORM_URL_MARKER = '/forms/j/'

/**
 * Accepts either a raw WeCom form id or a full "日报表单" link copied from the
 * WeCom Docs app/browser address bar, and extracts a clean form id from
 * either. Returns `null` for blank input or an id longer than the backend's
 * `WeComConnectionValidateRequest.form_id` bound (`max_length=128`,
 * `backend/app/schemas/wecom.py`) — never throws, so the caller can drive a
 * form validation message from the `null` result alone.
 */
export function parseWeComFormId(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) {
    return null
  }
  const markerIndex = trimmed.indexOf(FORM_URL_MARKER)
  const candidate =
    markerIndex === -1
      ? trimmed
      : trimmed.slice(markerIndex + FORM_URL_MARKER.length).split(/[?#/]/)[0]
  if (!candidate || candidate.length > MAX_FORM_ID_LENGTH) {
    return null
  }
  return candidate
}

const STATUS_LABELS: Record<WeComSyncStatus, string> = {
  pending: '待同步',
  syncing: '同步中',
  succeeded: '已同步',
  failed: '同步失败',
  auth_required: '登录已失效',
  schema_changed: '模板结构已变化',
  duplicate_detected: '疑似重复',
  uncertain: '结果不确定'
}

export function weComSyncStatusLabel(status: WeComSyncStatus): string {
  return STATUS_LABELS[status]
}

export type WeComSyncStatusTagType = 'success' | 'warning' | 'danger' | 'info'

const STATUS_TAG_TYPES: Record<WeComSyncStatus, WeComSyncStatusTagType> = {
  pending: 'info',
  syncing: 'warning',
  succeeded: 'success',
  failed: 'danger',
  auth_required: 'danger',
  schema_changed: 'danger',
  duplicate_detected: 'warning',
  uncertain: 'warning'
}

export function weComSyncStatusTagType(status: WeComSyncStatus): WeComSyncStatusTagType {
  return STATUS_TAG_TYPES[status]
}

// Mirrors `backend/app/services/wecom_sync.py::_RETRY_ALLOWED_SOURCE_STATUSES`.
// `uncertain` is deliberately excluded — `WeComSyncService.retry()` rejects it
// with `40914` (only remote reconciliation may resolve it, never a direct retry).
const RETRY_ELIGIBLE_STATUSES: readonly WeComSyncStatus[] = [
  'failed',
  'auth_required',
  'schema_changed',
  'duplicate_detected'
]

export function weComSyncIsRetryEligible(status: WeComSyncStatus): boolean {
  return RETRY_ELIGIBLE_STATUSES.includes(status)
}

/** History-table action: a fresh pending record may be synchronized and only
 * an explicit `failed` record may be retried directly. Authentication,
 * schema, duplicate and uncertain states all require an out-of-band user
 * action before the preview dialog can decide whether execution is safe. */
export function weComSyncActionLabel(status: WeComSyncStatus): string | null {
  if (status === 'pending') {
    return '同步'
  }
  if (status === 'failed') {
    return '重试'
  }
  return null
}

/** Best-effort human message for a sync record row: the server's own
 * `last_error_message` when present, else a generic sentence derived from
 * the status label. Never fabricates protocol detail the record doesn't
 * carry (`docs/方案设计.md` §11: 同步记录本身也不保存请求/响应原文). */
export function weComSyncSummary(record: WeComSyncRecordData): string {
  if (record.last_error_message) {
    return record.last_error_message
  }
  if (record.status === 'succeeded') {
    return '已成功同步到企业微信'
  }
  return weComSyncStatusLabel(record.status)
}

/** Custom fields a user can actually assign a mapping target to: enabled,
 * non-core (`core_type=today_work/tomorrow_plan` route automatically),
 * non-`PROJECT_LIST` (also routed automatically, into 今日工作内容) —
 * matches `backend/app/services/wecom_mapper.py::_route_entry`'s rule
 * ordering, and disabled fields can never carry a value in the first place
 * (`validate_daily_content` rejects them at save time). */
export function weComMappableTemplateFields(fields: TemplateFieldData[]): TemplateFieldData[] {
  return fields
    .filter(
      (field) => field.enabled && field.core_type === null && field.field_type !== 'PROJECT_LIST'
    )
    .sort((left, right) => left.sort_order - right.sort_order)
}

export function weComFieldMappingRuleTarget(
  rules: WeComFieldMappingRule[],
  fieldKey: string
): WeComFieldMappingTarget | null {
  return rules.find((rule) => rule.field_key === fieldKey)?.target ?? null
}

/** Pure add/update/remove for one field's mapping rule: `target=null` drops
 * any existing rule for `fieldKey` (back to "unmapped"), otherwise the rule
 * is inserted or its `target` is replaced. Returns a new array; never
 * mutates `rules`. */
export function upsertWeComFieldMappingRule(
  rules: WeComFieldMappingRule[],
  fieldKey: string,
  target: WeComFieldMappingTarget | null
): WeComFieldMappingRule[] {
  const withoutField = rules.filter((rule) => rule.field_key !== fieldKey)
  if (target === null) {
    return withoutField
  }
  return [...withoutField, { field_key: fieldKey, target }]
}

/** Replaces only the rules represented by the current template's mapping
 * table. Rules for historical template field keys remain untouched so saving
 * settings cannot erase mappings added from an archived-day preview. */
export function replaceVisibleWeComFieldMappingRules(
  existingRules: WeComFieldMappingRule[],
  visibleFieldKeys: string[],
  targets: Readonly<Record<string, WeComFieldMappingTarget | 'unmapped'>>
): WeComFieldMappingRule[] {
  const visibleKeys = new Set(visibleFieldKeys)
  let rules = existingRules.filter((rule) => !visibleKeys.has(rule.field_key))
  for (const fieldKey of visibleFieldKeys) {
    const target = targets[fieldKey]
    if (target !== undefined && target !== 'unmapped') {
      rules = upsertWeComFieldMappingRule(rules, fieldKey, target)
    }
  }
  return rules
}

// Mirrors `backend/app/schemas/wecom.py` (`docs/方案设计.md` §6.2-§6.4/§9.1)
// field for field. Only the shapes that actually cross the public
// `/api/v1/wecom/**` REST surface — the Main-only `/api/v1/internal/wecom/**`
// contracts never reach the renderer, they're consumed entirely inside
// Electron Main (`electron/src/main/wecom/bridge-client.ts`).

export type WeComBindingStatus = 'connected' | 'expired' | 'disconnected'

export interface WeComConnectionData {
  connected: boolean
  status: WeComBindingStatus | null
  wecom_vid: string | null
  display_name: string | null
  corp_id: string | null
  last_validated_at: string | null
  last_auth_error_at: string | null
}

export type WeComReplyType = 'text' | 'date' | 'select'

export interface WeComQuestionSpec {
  question_id: string
  reply_type: WeComReplyType
  sub_type: string | null
  submit_order: number
}

export interface WeComQuestionMappingConfig {
  schema_version: 1
  date_question: WeComQuestionSpec
  today_question: WeComQuestionSpec
  tomorrow_question: WeComQuestionSpec
}

export interface WeComRecipientConfig {
  schema_version: 1
  mngreporter_vids: string[]
  reporter_vids: string[]
  remote_version: number
}

export type WeComFieldMappingTarget = 'today_work' | 'tomorrow_plan' | 'ignore'
export type WeComUnmappedFieldPolicy = 'block' | 'ignore'

export interface WeComFieldMappingRule {
  field_key: string
  target: WeComFieldMappingTarget
}

export interface WeComFieldMappingConfig {
  schema_version: 1
  rules: WeComFieldMappingRule[]
  unmapped_policy: WeComUnmappedFieldPolicy
}

export interface WeComProfileData {
  form_id: string
  template_id: string
  destination_fingerprint: string
  schema_fingerprint: string
  question_mapping: WeComQuestionMappingConfig
  recipient_config: WeComRecipientConfig
  field_mapping: WeComFieldMappingConfig
  version: number
  is_active: boolean
}

export interface WeComProfileUpdateRequest {
  expected_version: number
  recipient_config?: WeComRecipientConfig
  field_mapping?: WeComFieldMappingConfig
}

export interface WeComPreviewData {
  date_answer: string
  today_work_answer: string
  tomorrow_plan_answer: string
  source_count: number
  today_work_char_count: number
  tomorrow_plan_char_count: number
  unmapped_field_keys: string[]
}

export type WeComSyncStatus =
  | 'pending'
  | 'syncing'
  | 'succeeded'
  | 'failed'
  | 'auth_required'
  | 'schema_changed'
  | 'duplicate_detected'
  | 'uncertain'

export interface WeComSyncRecordData {
  id: string
  daily_report_day_id: string
  work_date: string
  destination_fingerprint: string
  status: WeComSyncStatus
  attempt_count: number
  remote_answer_id: string | null
  remote_reply_id: string | null
  remote_journal_uuid: string | null
  last_error_kind: string | null
  last_error_message: string | null
  last_attempt_at: string | null
  succeeded_at: string | null
  created_at: string
  updated_at: string
}

export interface WeComSyncRecordCreateData extends WeComSyncRecordData {
  created: boolean
}

export interface WeComSyncRecordListData {
  items: WeComSyncRecordData[]
  page: number
  page_size: number
  total: number
}

export interface WeComSyncRecordQuery {
  status?: WeComSyncStatus
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export type ServiceState = 'pending' | 'ready' | 'failed'

export interface SidecarStatusSnapshot {
  state: ServiceState
  reason: string | null
  exitCode: number | null
  recentLogLines: string[]
  updatedAt: number
}

export interface RuntimeApiConfig {
  baseUrl: string
  runtimeSecretHeader: string
  runtimeSecret: string
}

export interface SecureTokenSnapshot {
  available: boolean
  token: string | null
  reason: 'secure-storage-unavailable' | null
}

export type ExportSaveStatus = 'saved' | 'canceled' | 'failed'

export interface ExportSaveResult {
  status: ExportSaveStatus
}

/** Manual backup downloads land through the same save-as flow as report
 * exports, so the outcome shape is identical; kept as its own alias so
 * backup call sites don't read as if they were exporting a report. */
export type BackupSaveResult = ExportSaveResult

export const RUNTIME_SECRET_HEADER = 'X-Runtime-Secret'

/** Env var used to hand the runtime secret to the sidecar process. Must match `WEEKLY_REPORT_RUNTIME_SECRET` read by `backend/app/core/config.py`. */
export const RUNTIME_SECRET_ENV_VAR = 'WEEKLY_REPORT_RUNTIME_SECRET'

export const IPC_CHANNELS = {
  SIDECAR_GET_STATUS: 'sidecar:get-status',
  SIDECAR_STATE_CHANGED: 'sidecar:state-changed',
  SIDECAR_RETRY: 'sidecar:retry',
  API_GET_CONFIG: 'api:get-config',
  TOKEN_GET: 'token:get',
  TOKEN_SET: 'token:set',
  TOKEN_CLEAR: 'token:clear',
  EXPORT_SAVE_FILE: 'export:save-file',
  BACKUP_SAVE_FILE: 'backup:save-file'
} as const

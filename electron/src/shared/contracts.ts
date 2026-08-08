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

/**
 * Header for the WeCom bridge's independent Main-only secret (`docs/方案设计.md`
 * §3.1/§9.2, decision SEC-014). Deliberately separate from `RUNTIME_SECRET_HEADER`:
 * the runtime secret reaches the renderer's API client via preload, so it cannot
 * guard endpoints that carry WeCom Cookies. This header/value pair must never be
 * exposed to preload or renderer code.
 */
export const MAIN_BRIDGE_SECRET_HEADER = 'X-Main-Bridge-Secret'

/** Env var used to hand the Main-only bridge secret to the sidecar process. Must match `WEEKLY_REPORT_MAIN_BRIDGE_SECRET` (read by FastAPI starting WECOM-06). */
export const MAIN_BRIDGE_SECRET_ENV_VAR = 'WEEKLY_REPORT_MAIN_BRIDGE_SECRET'

export const IPC_CHANNELS = {
  SIDECAR_GET_STATUS: 'sidecar:get-status',
  SIDECAR_STATE_CHANGED: 'sidecar:state-changed',
  SIDECAR_RETRY: 'sidecar:retry',
  API_GET_CONFIG: 'api:get-config',
  TOKEN_GET: 'token:get',
  TOKEN_SET: 'token:set',
  TOKEN_CLEAR: 'token:clear',
  EXPORT_SAVE_FILE: 'export:save-file',
  BACKUP_SAVE_FILE: 'backup:save-file',
  WECOM_CONNECT: 'wecom:connect',
  WECOM_DISCONNECT: 'wecom:disconnect',
  WECOM_EXECUTE_SYNC: 'wecom:execute-sync'
} as const

export type WeComConnectStatus = 'connected' | 'canceled' | 'failed'

export interface WeComConnectResult {
  status: WeComConnectStatus
  reason: string | null
}

export type WeComDisconnectStatus = 'disconnected' | 'failed'

export interface WeComDisconnectResult {
  status: WeComDisconnectStatus
  reason: string | null
}

export type WeComExecuteSyncStatus = 'submitted' | 'failed'

export interface WeComExecuteSyncResult {
  status: WeComExecuteSyncStatus
  reason: string | null
}

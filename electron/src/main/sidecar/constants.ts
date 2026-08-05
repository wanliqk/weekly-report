export const READY_LINE_TIMEOUT_MS = 15_000
export const HEALTH_POLL_INTERVAL_MS = 200
export const HEALTH_POLL_TIMEOUT_MS = 15_000
export const HEALTH_REQUEST_TIMEOUT_MS = 1_000
export const GRACEFUL_SHUTDOWN_TIMEOUT_MS = 5_000
export const LOG_BUFFER_MAX_LINES = 50

/** Must match the PyInstaller onedir output name produced by the future PKG-01 packaging task. */
export const PROD_SIDECAR_EXECUTABLE_NAME = 'weekly-report-backend.exe'

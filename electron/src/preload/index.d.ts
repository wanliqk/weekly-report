import type {
  BackupSaveResult,
  ExportSaveResult,
  RuntimeApiConfig,
  SecureTokenSnapshot,
  SidecarStatusSnapshot
} from '../shared/contracts'

declare global {
  interface Window {
    readonly desktop: {
      readonly platform: NodeJS.Platform
    }
    readonly runtimeBridge: {
      readonly sidecar: {
        readonly getStatus: () => Promise<SidecarStatusSnapshot>
        readonly onStatusChange: (listener: (snapshot: SidecarStatusSnapshot) => void) => () => void
        readonly retry: () => Promise<SidecarStatusSnapshot>
      }
      readonly api: {
        readonly getConfig: () => Promise<RuntimeApiConfig | null>
      }
      readonly token: {
        readonly get: () => Promise<SecureTokenSnapshot>
        readonly set: (token: string) => Promise<SecureTokenSnapshot>
        readonly clear: () => Promise<SecureTokenSnapshot>
      }
      readonly exportFile: {
        readonly save: (suggestedName: string, data: Uint8Array) => Promise<ExportSaveResult>
      }
      readonly backupFile: {
        readonly save: (suggestedName: string, data: Uint8Array) => Promise<BackupSaveResult>
      }
    }
  }
}

export {}

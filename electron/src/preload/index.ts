import { contextBridge, ipcRenderer } from 'electron'
import type { IpcRendererEvent } from 'electron'

import {
  IPC_CHANNELS,
  type BackupSaveResult,
  type ExportSaveResult,
  type RuntimeApiConfig,
  type SecureTokenSnapshot,
  type SidecarStatusSnapshot,
  type WeComConnectResult,
  type WeComDisconnectResult,
  type WeComExecuteSyncResult
} from '../shared/contracts'

const desktopApi = Object.freeze({
  platform: process.platform
})

const runtimeBridge = Object.freeze({
  sidecar: Object.freeze({
    getStatus: (): Promise<SidecarStatusSnapshot> =>
      ipcRenderer.invoke(IPC_CHANNELS.SIDECAR_GET_STATUS),
    onStatusChange: (listener: (snapshot: SidecarStatusSnapshot) => void): (() => void) => {
      const handler = (_event: IpcRendererEvent, snapshot: SidecarStatusSnapshot): void =>
        listener(snapshot)
      ipcRenderer.on(IPC_CHANNELS.SIDECAR_STATE_CHANGED, handler)
      return () => ipcRenderer.removeListener(IPC_CHANNELS.SIDECAR_STATE_CHANGED, handler)
    },
    retry: (): Promise<SidecarStatusSnapshot> => ipcRenderer.invoke(IPC_CHANNELS.SIDECAR_RETRY)
  }),
  api: Object.freeze({
    getConfig: (): Promise<RuntimeApiConfig | null> =>
      ipcRenderer.invoke(IPC_CHANNELS.API_GET_CONFIG)
  }),
  token: Object.freeze({
    get: (): Promise<SecureTokenSnapshot> => ipcRenderer.invoke(IPC_CHANNELS.TOKEN_GET),
    set: (token: string): Promise<SecureTokenSnapshot> =>
      ipcRenderer.invoke(IPC_CHANNELS.TOKEN_SET, token),
    clear: (): Promise<SecureTokenSnapshot> => ipcRenderer.invoke(IPC_CHANNELS.TOKEN_CLEAR)
  }),
  exportFile: Object.freeze({
    save: (suggestedName: string, data: Uint8Array): Promise<ExportSaveResult> =>
      ipcRenderer.invoke(IPC_CHANNELS.EXPORT_SAVE_FILE, { suggestedName, data })
  }),
  backupFile: Object.freeze({
    save: (suggestedName: string, data: Uint8Array): Promise<BackupSaveResult> =>
      ipcRenderer.invoke(IPC_CHANNELS.BACKUP_SAVE_FILE, { suggestedName, data })
  }),
  // Deliberately narrow (docs/方案设计.md §9.3): connect/disconnect/executeSync
  // only. Never expose reading Cookies, sending arbitrary HTTP, opening
  // arbitrary URLs, or reading the credential file path.
  wecom: Object.freeze({
    connect: (): Promise<WeComConnectResult> => ipcRenderer.invoke(IPC_CHANNELS.WECOM_CONNECT),
    disconnect: (): Promise<WeComDisconnectResult> =>
      ipcRenderer.invoke(IPC_CHANNELS.WECOM_DISCONNECT),
    executeSync: (recordId: string): Promise<WeComExecuteSyncResult> =>
      ipcRenderer.invoke(IPC_CHANNELS.WECOM_EXECUTE_SYNC, recordId)
  })
})

contextBridge.exposeInMainWorld('desktop', desktopApi)
contextBridge.exposeInMainWorld('runtimeBridge', runtimeBridge)

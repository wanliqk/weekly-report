import { contextBridge, ipcRenderer } from 'electron'
import type { IpcRendererEvent } from 'electron'

import {
  IPC_CHANNELS,
  type RuntimeApiConfig,
  type SecureTokenSnapshot,
  type SidecarStatusSnapshot
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
  })
})

contextBridge.exposeInMainWorld('desktop', desktopApi)
contextBridge.exposeInMainWorld('runtimeBridge', runtimeBridge)

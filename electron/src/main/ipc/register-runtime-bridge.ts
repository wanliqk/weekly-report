import type { BrowserWindow, IpcMainInvokeEvent } from 'electron'
import { ipcMain } from 'electron'

import {
  IPC_CHANNELS,
  RUNTIME_SECRET_HEADER,
  type ExportSaveResult,
  type RuntimeApiConfig,
  type SecureTokenSnapshot,
  type SidecarStatusSnapshot
} from '../../shared/contracts'
import type { ExportFileSaver } from '../export/file-saver'
import type { SecureTokenStore } from '../security/secure-token-store'
import type { SidecarManager } from '../sidecar/manager'

function assertTrustedSender(event: IpcMainInvokeEvent, window: BrowserWindow): void {
  if (event.senderFrame !== window.webContents.mainFrame) {
    throw new Error('rejected IPC call from an untrusted frame')
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** Wires the sidecar manager to the small, purpose-named IPC surface the preload script exposes. Returns a disposer to call when the owning window is destroyed. */
export function registerRuntimeBridge(
  manager: SidecarManager,
  window: BrowserWindow,
  tokenStore: SecureTokenStore,
  exportFileSaver: ExportFileSaver
): () => void {
  ipcMain.handle(IPC_CHANNELS.SIDECAR_GET_STATUS, (event): SidecarStatusSnapshot => {
    assertTrustedSender(event, window)
    return manager.getSnapshot()
  })

  ipcMain.handle(IPC_CHANNELS.SIDECAR_RETRY, async (event): Promise<SidecarStatusSnapshot> => {
    assertTrustedSender(event, window)
    await manager.retry()
    return manager.getSnapshot()
  })

  ipcMain.handle(IPC_CHANNELS.API_GET_CONFIG, (event): RuntimeApiConfig | null => {
    assertTrustedSender(event, window)
    const config = manager.getRuntimeConfig()
    if (!config) {
      return null
    }
    return {
      baseUrl: config.baseUrl,
      runtimeSecretHeader: RUNTIME_SECRET_HEADER,
      runtimeSecret: config.runtimeSecret
    }
  })

  ipcMain.handle(IPC_CHANNELS.TOKEN_GET, async (event): Promise<SecureTokenSnapshot> => {
    assertTrustedSender(event, window)
    return tokenStore.getToken()
  })

  ipcMain.handle(
    IPC_CHANNELS.TOKEN_SET,
    async (event, token: unknown): Promise<SecureTokenSnapshot> => {
      assertTrustedSender(event, window)
      if (typeof token !== 'string') {
        throw new Error('rejected invalid token payload')
      }
      return tokenStore.setToken(token)
    }
  )

  ipcMain.handle(IPC_CHANNELS.TOKEN_CLEAR, async (event): Promise<SecureTokenSnapshot> => {
    assertTrustedSender(event, window)
    return tokenStore.clearToken()
  })

  ipcMain.handle(
    IPC_CHANNELS.EXPORT_SAVE_FILE,
    async (event, payload: unknown): Promise<ExportSaveResult> => {
      assertTrustedSender(event, window)
      if (!isRecord(payload)) {
        throw new Error('rejected invalid export save payload')
      }
      return exportFileSaver.save(payload.suggestedName, payload.data)
    }
  )

  const forwardStateChange = (snapshot: SidecarStatusSnapshot): void => {
    if (window.isDestroyed()) {
      return
    }
    window.webContents.send(IPC_CHANNELS.SIDECAR_STATE_CHANGED, snapshot)
  }
  manager.on('state-changed', forwardStateChange)

  return () => {
    ipcMain.removeHandler(IPC_CHANNELS.SIDECAR_GET_STATUS)
    ipcMain.removeHandler(IPC_CHANNELS.SIDECAR_RETRY)
    ipcMain.removeHandler(IPC_CHANNELS.API_GET_CONFIG)
    ipcMain.removeHandler(IPC_CHANNELS.TOKEN_GET)
    ipcMain.removeHandler(IPC_CHANNELS.TOKEN_SET)
    ipcMain.removeHandler(IPC_CHANNELS.TOKEN_CLEAR)
    ipcMain.removeHandler(IPC_CHANNELS.EXPORT_SAVE_FILE)
    manager.off('state-changed', forwardStateChange)
  }
}

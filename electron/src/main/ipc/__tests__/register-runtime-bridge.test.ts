import { EventEmitter } from 'node:events'

import type { BrowserWindow, IpcMainInvokeEvent } from 'electron'
import { beforeEach, describe, expect, it, vi } from 'vitest'

type Handler = (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown

const handlers = new Map<string, Handler>()

vi.mock('electron', () => ({
  ipcMain: {
    handle: vi.fn((channel: string, handler: Handler) => {
      handlers.set(channel, handler)
    }),
    removeHandler: vi.fn((channel: string) => {
      handlers.delete(channel)
    })
  }
}))

import { IPC_CHANNELS, type SidecarStatusSnapshot } from '../../../shared/contracts'
import type { ExportFileSaver } from '../../export/file-saver'
import type { SidecarManager } from '../../sidecar/manager'
import type { SecureTokenStore } from '../../security/secure-token-store'
import { registerRuntimeBridge } from '../register-runtime-bridge'

function snapshot(): SidecarStatusSnapshot {
  return { state: 'ready', reason: null, exitCode: null, recentLogLines: [], updatedAt: 0 }
}

class FakeManager extends EventEmitter {
  getSnapshot = vi.fn(snapshot)
  getRuntimeConfig = vi.fn(() => ({ baseUrl: 'http://127.0.0.1:1234', runtimeSecret: 'abc' }))
  retry = vi.fn().mockResolvedValue(undefined)
}

class FakeTokenStore {
  getToken = vi.fn().mockResolvedValue({ available: true, token: null, reason: null })
  setToken = vi.fn().mockResolvedValue({ available: true, token: null, reason: null })
  clearToken = vi.fn().mockResolvedValue({ available: true, token: null, reason: null })
}

class FakeExportFileSaver {
  save = vi.fn().mockResolvedValue({ status: 'saved' })
}

function register(
  manager: FakeManager,
  window: BrowserWindow,
  exportFileSaver: FakeExportFileSaver = new FakeExportFileSaver()
): () => void {
  return registerRuntimeBridge(
    manager as unknown as SidecarManager,
    window,
    new FakeTokenStore() as unknown as SecureTokenStore,
    exportFileSaver as unknown as ExportFileSaver
  )
}

function createWindow(mainFrame: object): {
  window: BrowserWindow
  send: ReturnType<typeof vi.fn>
} {
  const send = vi.fn()
  const window = {
    isDestroyed: () => false,
    webContents: { mainFrame, send }
  } as unknown as BrowserWindow
  return { window, send }
}

describe('registerRuntimeBridge', () => {
  beforeEach(() => {
    handlers.clear()
  })

  it('rejects invoke calls from a frame other than the window main frame', () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    register(manager, window)

    const handler = handlers.get(IPC_CHANNELS.SIDECAR_GET_STATUS)
    expect(handler).toBeDefined()
    expect(() => handler?.({ senderFrame: {} } as IpcMainInvokeEvent)).toThrow()
    expect(manager.getSnapshot).not.toHaveBeenCalled()
  })

  it('serves the snapshot for calls from the trusted main frame', () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    register(manager, window)

    const handler = handlers.get(IPC_CHANNELS.SIDECAR_GET_STATUS)
    const result = handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(manager.getSnapshot).toHaveBeenCalledTimes(1)
    expect(result).toEqual(snapshot())
  })

  it('forwards state-changed events to the window', () => {
    const mainFrame = {}
    const { window, send } = createWindow(mainFrame)
    const manager = new FakeManager()
    register(manager, window)

    const nextSnapshot = { ...snapshot(), state: 'failed' as const }
    manager.emit('state-changed', nextSnapshot)

    expect(send).toHaveBeenCalledWith(IPC_CHANNELS.SIDECAR_STATE_CHANGED, nextSnapshot)
  })

  it('the disposer removes all handlers and unsubscribes from state changes', () => {
    const mainFrame = {}
    const { window, send } = createWindow(mainFrame)
    const manager = new FakeManager()
    const dispose = register(manager, window)

    dispose()
    manager.emit('state-changed', snapshot())

    expect(handlers.size).toBe(0)
    expect(send).not.toHaveBeenCalled()
  })

  it('validates the token payload before handing it to secure storage', async () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    const tokenStore = new FakeTokenStore()
    registerRuntimeBridge(
      manager as unknown as SidecarManager,
      window,
      tokenStore as unknown as SecureTokenStore,
      new FakeExportFileSaver() as unknown as ExportFileSaver
    )

    const handler = handlers.get(IPC_CHANNELS.TOKEN_SET)
    await expect(handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, 123)).rejects.toThrow()
    expect(tokenStore.setToken).not.toHaveBeenCalled()
  })

  it('rejects export save-file calls from an untrusted frame', async () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    const exportFileSaver = new FakeExportFileSaver()
    register(manager, window, exportFileSaver)

    const handler = handlers.get(IPC_CHANNELS.EXPORT_SAVE_FILE)
    await expect(
      handler?.({ senderFrame: {} } as IpcMainInvokeEvent, { suggestedName: 'a.xlsx', data: {} })
    ).rejects.toThrow()
    expect(exportFileSaver.save).not.toHaveBeenCalled()
  })

  it('rejects export save-file calls whose payload is not an object', async () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    const exportFileSaver = new FakeExportFileSaver()
    register(manager, window, exportFileSaver)

    const handler = handlers.get(IPC_CHANNELS.EXPORT_SAVE_FILE)
    await expect(
      handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, 'not-an-object')
    ).rejects.toThrow()
    expect(exportFileSaver.save).not.toHaveBeenCalled()
  })

  it('delegates a well-formed export save-file call to the saver', async () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    const exportFileSaver = new FakeExportFileSaver()
    register(manager, window, exportFileSaver)

    const handler = handlers.get(IPC_CHANNELS.EXPORT_SAVE_FILE)
    const data = new Uint8Array([1, 2, 3])
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, {
      suggestedName: 'report.xlsx',
      data
    })

    expect(exportFileSaver.save).toHaveBeenCalledWith('report.xlsx', data)
    expect(result).toEqual({ status: 'saved' })
  })
})

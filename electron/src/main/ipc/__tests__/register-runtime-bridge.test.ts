import { EventEmitter } from 'node:events'

import type { BrowserWindow, IpcMainInvokeEvent } from 'electron'
import { beforeEach, describe, expect, it, vi } from 'vitest'

type Handler = (event: IpcMainInvokeEvent) => unknown

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
import type { SidecarManager } from '../../sidecar/manager'
import { registerRuntimeBridge } from '../register-runtime-bridge'

function snapshot(): SidecarStatusSnapshot {
  return { state: 'ready', reason: null, exitCode: null, recentLogLines: [], updatedAt: 0 }
}

class FakeManager extends EventEmitter {
  getSnapshot = vi.fn(snapshot)
  getRuntimeConfig = vi.fn(() => ({ baseUrl: 'http://127.0.0.1:1234', runtimeSecret: 'abc' }))
  retry = vi.fn().mockResolvedValue(undefined)
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
    registerRuntimeBridge(manager as unknown as SidecarManager, window)

    const handler = handlers.get(IPC_CHANNELS.SIDECAR_GET_STATUS)
    expect(handler).toBeDefined()
    expect(() => handler?.({ senderFrame: {} } as IpcMainInvokeEvent)).toThrow()
    expect(manager.getSnapshot).not.toHaveBeenCalled()
  })

  it('serves the snapshot for calls from the trusted main frame', () => {
    const mainFrame = {}
    const { window } = createWindow(mainFrame)
    const manager = new FakeManager()
    registerRuntimeBridge(manager as unknown as SidecarManager, window)

    const handler = handlers.get(IPC_CHANNELS.SIDECAR_GET_STATUS)
    const result = handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(manager.getSnapshot).toHaveBeenCalledTimes(1)
    expect(result).toEqual(snapshot())
  })

  it('forwards state-changed events to the window', () => {
    const mainFrame = {}
    const { window, send } = createWindow(mainFrame)
    const manager = new FakeManager()
    registerRuntimeBridge(manager as unknown as SidecarManager, window)

    const nextSnapshot = { ...snapshot(), state: 'failed' as const }
    manager.emit('state-changed', nextSnapshot)

    expect(send).toHaveBeenCalledWith(IPC_CHANNELS.SIDECAR_STATE_CHANGED, nextSnapshot)
  })

  it('the disposer removes all handlers and unsubscribes from state changes', () => {
    const mainFrame = {}
    const { window, send } = createWindow(mainFrame)
    const manager = new FakeManager()
    const dispose = registerRuntimeBridge(manager as unknown as SidecarManager, window)

    dispose()
    manager.emit('state-changed', snapshot())

    expect(handlers.size).toBe(0)
    expect(send).not.toHaveBeenCalled()
  })
})

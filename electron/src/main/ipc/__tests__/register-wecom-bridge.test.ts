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

import { IPC_CHANNELS } from '../../../shared/contracts'
import type { WeComAuthWindowController } from '../../wecom/auth-window-controller'
import type { WeComBridgeClient } from '../../wecom/bridge-client'
import type { WeComCredentialStore } from '../../security/wecom-credential-store'
import {
  createInMemoryWeComBridgeState,
  registerWeComBridge,
  type WeComBridgeState
} from '../register-wecom-bridge'

const VALID_ULID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'

function createWindow(mainFrame: object): BrowserWindow {
  return { webContents: { mainFrame } } as unknown as BrowserWindow
}

class FakeAuthWindowController {
  connect = vi.fn()
}

class FakeCredentialStore {
  save = vi.fn()
  load = vi.fn()
  delete = vi.fn().mockResolvedValue(undefined)
}

class FakeBridgeClient {
  validateConnection = vi.fn()
  disconnect = vi.fn().mockResolvedValue({ status: 'disconnected' })
  executeSync = vi.fn()
}

function register(
  window: BrowserWindow,
  authWindowController: FakeAuthWindowController,
  credentialStore: FakeCredentialStore,
  bridgeClient: FakeBridgeClient,
  state: WeComBridgeState = createInMemoryWeComBridgeState()
): () => void {
  return registerWeComBridge(
    window,
    authWindowController as unknown as WeComAuthWindowController,
    credentialStore as unknown as WeComCredentialStore,
    bridgeClient as unknown as WeComBridgeClient,
    state
  )
}

describe('registerWeComBridge', () => {
  beforeEach(() => {
    handlers.clear()
  })

  it('rejects connect calls from an untrusted frame without starting the login flow', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const authWindowController = new FakeAuthWindowController()
    register(window, authWindowController, new FakeCredentialStore(), new FakeBridgeClient())

    const handler = handlers.get(IPC_CHANNELS.WECOM_CONNECT)
    await expect(handler?.({ senderFrame: {} } as IpcMainInvokeEvent)).rejects.toThrow()
    expect(authWindowController.connect).not.toHaveBeenCalled()
  })

  it('rejects disconnect calls from an untrusted frame', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const credentialStore = new FakeCredentialStore()
    register(window, new FakeAuthWindowController(), credentialStore, new FakeBridgeClient())

    const handler = handlers.get(IPC_CHANNELS.WECOM_DISCONNECT)
    await expect(handler?.({ senderFrame: {} } as IpcMainInvokeEvent)).rejects.toThrow()
    expect(credentialStore.delete).not.toHaveBeenCalled()
  })

  it('rejects executeSync calls from an untrusted frame', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const bridgeClient = new FakeBridgeClient()
    register(window, new FakeAuthWindowController(), new FakeCredentialStore(), bridgeClient)

    const handler = handlers.get(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
    await expect(handler?.({ senderFrame: {} } as IpcMainInvokeEvent, VALID_ULID)).rejects.toThrow()
    expect(bridgeClient.executeSync).not.toHaveBeenCalled()
  })

  describe('executeSync record id validation', () => {
    const invalidIds = [
      '',
      'too-short',
      '01ARZ3NDEKTSV4RRFFQ69G5FA', // 25 chars
      '01ARZ3NDEKTSV4RRFFQ69G5FAVX', // 27 chars
      '01ARZ3NDEKTSV4RRFFQ69G5FAI', // contains excluded letter I
      '01arz3ndektsv4rrffq69g5fav', // lowercase
      'not-a-ulid-at-all-000000000'
    ]

    it.each(invalidIds)(
      'rejects invalid record id %j without calling the bridge client',
      async (recordId) => {
        const mainFrame = {}
        const window = createWindow(mainFrame)
        const bridgeClient = new FakeBridgeClient()
        const state = createInMemoryWeComBridgeState()
        state.setActiveSlot('a'.repeat(32))
        register(
          window,
          new FakeAuthWindowController(),
          new FakeCredentialStore(),
          bridgeClient,
          state
        )

        const handler = handlers.get(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
        await expect(
          handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, recordId)
        ).rejects.toThrow()
        expect(bridgeClient.executeSync).not.toHaveBeenCalled()
      }
    )

    const validIds = [
      '01ARZ3NDEKTSV4RRFFQ69G5FAV',
      '7ZZZZZZZZZZZZZZZZZZZZZZZZZ',
      '00000000000000000000000000'.slice(0, 26)
    ]

    it.each(validIds)(
      'accepts valid ULID %s and proceeds to look up credentials',
      async (recordId) => {
        const mainFrame = {}
        const window = createWindow(mainFrame)
        const credentialStore = new FakeCredentialStore()
        const bridgeClient = new FakeBridgeClient()
        bridgeClient.executeSync.mockResolvedValue({ status: 'submitted' })
        const state = createInMemoryWeComBridgeState()
        const slot = 'b'.repeat(32)
        state.setActiveSlot(slot)
        credentialStore.load.mockResolvedValue([
          {
            name: 'wedoc_sid',
            value: 'v',
            domain: 'doc.weixin.qq.com',
            path: '/',
            secure: true,
            httpOnly: true,
            sameSite: 'lax',
            expirationDate: null
          }
        ])
        register(window, new FakeAuthWindowController(), credentialStore, bridgeClient, state)

        const handler = handlers.get(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
        const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, recordId)

        expect(credentialStore.load).toHaveBeenCalledWith(slot)
        expect(bridgeClient.executeSync).toHaveBeenCalledWith(recordId, expect.any(Array))
        expect(result).toEqual({ status: 'submitted', reason: null })
      }
    )
  })

  it('executeSync fails cleanly when there is no active connection', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const bridgeClient = new FakeBridgeClient()
    register(window, new FakeAuthWindowController(), new FakeCredentialStore(), bridgeClient)

    const handler = handlers.get(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent, VALID_ULID)

    expect(result).toEqual({ status: 'failed', reason: expect.any(String) })
    expect(bridgeClient.executeSync).not.toHaveBeenCalled()
  })

  it('connect() cleans up the newly created credential slot when bridge validation fails', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const authWindowController = new FakeAuthWindowController()
    authWindowController.connect.mockResolvedValue({
      status: 'success',
      cookieJar: [{ name: 'wedoc_sid', value: 'v' }]
    })
    const credentialStore = new FakeCredentialStore()
    credentialStore.save.mockResolvedValue('c'.repeat(32))
    const bridgeClient = new FakeBridgeClient()
    bridgeClient.validateConnection.mockRejectedValue(
      new Error('backend endpoint not implemented yet')
    )
    const state = createInMemoryWeComBridgeState()
    register(window, authWindowController, credentialStore, bridgeClient, state)

    const handler = handlers.get(IPC_CHANNELS.WECOM_CONNECT)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(result).toEqual({ status: 'failed', reason: expect.any(String) })
    expect(credentialStore.delete).toHaveBeenCalledWith('c'.repeat(32))
    expect(state.getActiveSlot()).toBeNull()
  })

  it('connect() keeps the credential slot active and returns connected on full success', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const authWindowController = new FakeAuthWindowController()
    authWindowController.connect.mockResolvedValue({
      status: 'success',
      cookieJar: [{ name: 'wedoc_sid', value: 'v' }]
    })
    const credentialStore = new FakeCredentialStore()
    credentialStore.save.mockResolvedValue('d'.repeat(32))
    const bridgeClient = new FakeBridgeClient()
    bridgeClient.validateConnection.mockResolvedValue({ status: 'connected' })
    const state = createInMemoryWeComBridgeState()
    register(window, authWindowController, credentialStore, bridgeClient, state)

    const handler = handlers.get(IPC_CHANNELS.WECOM_CONNECT)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(result).toEqual({ status: 'connected', reason: null })
    expect(credentialStore.delete).not.toHaveBeenCalled()
    expect(state.getActiveSlot()).toBe('d'.repeat(32))
  })

  it('connect() reports canceled without touching the credential store', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const authWindowController = new FakeAuthWindowController()
    authWindowController.connect.mockResolvedValue({ status: 'canceled' })
    const credentialStore = new FakeCredentialStore()
    register(window, authWindowController, credentialStore, new FakeBridgeClient())

    const handler = handlers.get(IPC_CHANNELS.WECOM_CONNECT)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(result).toEqual({ status: 'canceled', reason: null })
    expect(credentialStore.save).not.toHaveBeenCalled()
  })

  it('disconnect() deletes the credential file before notifying the backend', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const credentialStore = new FakeCredentialStore()
    const bridgeClient = new FakeBridgeClient()
    const callOrder: string[] = []
    credentialStore.delete.mockImplementation(async () => {
      callOrder.push('delete-credential')
    })
    bridgeClient.disconnect.mockImplementation(async () => {
      callOrder.push('notify-backend')
      return { status: 'disconnected' }
    })
    const state = createInMemoryWeComBridgeState()
    state.setActiveSlot('e'.repeat(32))
    register(window, new FakeAuthWindowController(), credentialStore, bridgeClient, state)

    const handler = handlers.get(IPC_CHANNELS.WECOM_DISCONNECT)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(callOrder).toEqual(['delete-credential', 'notify-backend'])
    expect(result).toEqual({ status: 'disconnected', reason: null })
    expect(state.getActiveSlot()).toBeNull()
  })

  it('disconnect() still notifies the backend when there was no active slot to delete', async () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const credentialStore = new FakeCredentialStore()
    const bridgeClient = new FakeBridgeClient()
    register(window, new FakeAuthWindowController(), credentialStore, bridgeClient)

    const handler = handlers.get(IPC_CHANNELS.WECOM_DISCONNECT)
    const result = await handler?.({ senderFrame: mainFrame } as IpcMainInvokeEvent)

    expect(credentialStore.delete).not.toHaveBeenCalled()
    expect(bridgeClient.disconnect).toHaveBeenCalledTimes(1)
    expect(result).toEqual({ status: 'disconnected', reason: null })
  })

  it('the disposer removes all three wecom handlers', () => {
    const mainFrame = {}
    const window = createWindow(mainFrame)
    const dispose = register(
      window,
      new FakeAuthWindowController(),
      new FakeCredentialStore(),
      new FakeBridgeClient()
    )

    dispose()

    expect(handlers.has(IPC_CHANNELS.WECOM_CONNECT)).toBe(false)
    expect(handlers.has(IPC_CHANNELS.WECOM_DISCONNECT)).toBe(false)
    expect(handlers.has(IPC_CHANNELS.WECOM_EXECUTE_SYNC)).toBe(false)
  })
})

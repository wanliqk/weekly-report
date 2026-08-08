import type { BrowserWindow, IpcMainInvokeEvent } from 'electron'
import { ipcMain } from 'electron'

import {
  IPC_CHANNELS,
  type WeComConnectResult,
  type WeComDisconnectResult,
  type WeComExecuteSyncResult
} from '../../shared/contracts'
import type { WeComCredentialStore } from '../security/wecom-credential-store'
import type { WeComAuthWindowController } from '../wecom/auth-window-controller'
import type { WeComBridgeClient } from '../wecom/bridge-client'

// Matches `backend/app/core/ulid.py`: 26 Crockford-Base32 characters (I/L/O/U
// excluded from the alphabet). docs/方案设计.md §9.3: "recordId 必须符合 ULID
// 格式...格式不对直接拒绝，不传给下游".
const ULID_PATTERN = /^[0-9A-HJKMNP-TV-Z]{26}$/

function assertTrustedSender(event: IpcMainInvokeEvent, window: BrowserWindow): void {
  if (event.senderFrame !== window.webContents.mainFrame) {
    throw new Error('rejected IPC call from an untrusted frame')
  }
}

/** Tracks which credential slot (if any) belongs to the current connected
 * session, entirely in Main-process memory — never persisted, never exposed
 * to preload/renderer. `register-wecom-bridge.ts`'s own small piece of state,
 * separate from `WeComCredentialStore` (which only knows how to read/write a
 * slot it's given, not which slot is "current"). */
export interface WeComBridgeState {
  getActiveSlot: () => string | null
  setActiveSlot: (slot: string | null) => void
}

export function createInMemoryWeComBridgeState(): WeComBridgeState {
  let activeSlot: string | null = null
  return {
    getActiveSlot: () => activeSlot,
    setActiveSlot: (slot) => {
      activeSlot = slot
    }
  }
}

function toReason(error: unknown, fallback: string): string {
  return error instanceof Error && error.message.length > 0 ? error.message : fallback
}

async function connect(
  authWindowController: WeComAuthWindowController,
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient,
  state: WeComBridgeState
): Promise<WeComConnectResult> {
  const outcome = await authWindowController.connect()

  if (outcome.status === 'canceled') {
    return { status: 'canceled', reason: null }
  }
  if (outcome.status === 'timeout') {
    return { status: 'failed', reason: '登录超时，请重试' }
  }
  if (outcome.status === 'failed') {
    return { status: 'failed', reason: outcome.reason }
  }

  let slot: string
  try {
    slot = await credentialStore.save(outcome.cookieJar)
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法保存企业微信登录状态') }
  }

  try {
    // form_id resolution (the per-org WeDoc form) is WECOM-06/07 scope; this
    // task only wires the Main-only bridge call itself (docs/方案设计.md §5.1
    // step 4's "任一步失败时删除本次新建的凭证槽" is what's under test here).
    await bridgeClient.validateConnection(outcome.cookieJar, '')
  } catch (error) {
    await credentialStore.delete(slot).catch(() => {})
    return { status: 'failed', reason: toReason(error, '连接校验失败') }
  }

  state.setActiveSlot(slot)
  return { status: 'connected', reason: null }
}

async function disconnect(
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient,
  state: WeComBridgeState
): Promise<WeComDisconnectResult> {
  const slot = state.getActiveSlot()
  if (slot !== null) {
    try {
      await credentialStore.delete(slot)
    } catch (error) {
      return { status: 'failed', reason: toReason(error, '无法清除企业微信登录状态') }
    }
    state.setActiveSlot(null)
  }

  try {
    await bridgeClient.disconnect()
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法通知后端断开连接') }
  }
  return { status: 'disconnected', reason: null }
}

async function executeSync(
  recordId: string,
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient,
  state: WeComBridgeState
): Promise<WeComExecuteSyncResult> {
  const slot = state.getActiveSlot()
  if (slot === null) {
    return { status: 'failed', reason: '企业微信尚未连接，请先登录' }
  }

  let cookieJar
  try {
    cookieJar = await credentialStore.load(slot)
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法读取企业微信登录状态') }
  }
  if (cookieJar === null) {
    state.setActiveSlot(null)
    return { status: 'failed', reason: '企业微信登录状态已丢失，请重新登录' }
  }

  try {
    await bridgeClient.executeSync(recordId, cookieJar)
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '同步执行失败') }
  }
  return { status: 'submitted', reason: null }
}

/**
 * Registers the narrow `runtimeBridge.wecom` IPC surface (docs/方案设计.md §9.3):
 * `connect()`/`disconnect()`/`executeSync(recordId)` only — never "read Cookie",
 * "send arbitrary HTTP", or "open arbitrary URL". Kept in its own file (not folded
 * into `register-runtime-bridge.ts`) so the WeCom bridge doesn't couple to the
 * unrelated sidecar/token/export IPC surface. Returns a disposer, mirroring
 * `registerRuntimeBridge`.
 */
export function registerWeComBridge(
  window: BrowserWindow,
  authWindowController: WeComAuthWindowController,
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient,
  state: WeComBridgeState = createInMemoryWeComBridgeState()
): () => void {
  ipcMain.handle(IPC_CHANNELS.WECOM_CONNECT, async (event): Promise<WeComConnectResult> => {
    assertTrustedSender(event, window)
    return connect(authWindowController, credentialStore, bridgeClient, state)
  })

  ipcMain.handle(IPC_CHANNELS.WECOM_DISCONNECT, async (event): Promise<WeComDisconnectResult> => {
    assertTrustedSender(event, window)
    return disconnect(credentialStore, bridgeClient, state)
  })

  ipcMain.handle(
    IPC_CHANNELS.WECOM_EXECUTE_SYNC,
    async (event, recordId: unknown): Promise<WeComExecuteSyncResult> => {
      assertTrustedSender(event, window)
      if (typeof recordId !== 'string' || !ULID_PATTERN.test(recordId)) {
        throw new Error('rejected invalid record id payload')
      }
      return executeSync(recordId, credentialStore, bridgeClient, state)
    }
  )

  return () => {
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_CONNECT)
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_DISCONNECT)
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
  }
}

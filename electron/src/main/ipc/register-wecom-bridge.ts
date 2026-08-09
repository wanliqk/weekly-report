import type { BrowserWindow, IpcMainInvokeEvent } from 'electron'
import { ipcMain } from 'electron'

import {
  IPC_CHANNELS,
  type WeComConnectResult,
  type WeComDisconnectResult,
  type WeComExecuteSyncResult
} from '../../shared/contracts'
import type { WeComCookie, WeComCredentialStore } from '../security/wecom-credential-store'
import type { WeComAuthWindowController } from '../wecom/auth-window-controller'
import type { WeComBridgeClient } from '../wecom/bridge-client'

// Matches `backend/app/core/ulid.py`: 26 Crockford-Base32 characters (I/L/O/U
// excluded from the alphabet). docs/方案设计.md §9.3: "recordId 必须符合 ULID
// 格式...格式不对直接拒绝，不传给下游".
const ULID_PATTERN = /^[0-9A-HJKMNP-TV-Z]{26}$/

// Mirrors `backend/app/schemas/wecom.py`'s `WeComConnectionValidateRequest.form_id`
// (`Field(max_length=128)`); this is just a boundary sanity check (empty/absurdly
// long/non-string payloads rejected before opening a real login window), not a
// claim about WeCom's own id format — the renderer is expected to have already
// extracted a clean id via `parseWeComFormId()` before calling `connect()`.
const MAX_FORM_ID_LENGTH = 128

function isValidFormId(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= MAX_FORM_ID_LENGTH
}

function assertTrustedSender(event: IpcMainInvokeEvent, window: BrowserWindow): void {
  if (event.senderFrame !== window.webContents.mainFrame) {
    throw new Error('rejected IPC call from an untrusted frame')
  }
}

function toReason(error: unknown, fallback: string): string {
  return error instanceof Error && error.message.length > 0 ? error.message : fallback
}

async function connect(
  formId: string,
  authWindowController: WeComAuthWindowController,
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient
): Promise<WeComConnectResult> {
  try {
    await credentialStore.retryPendingDeletes()
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法清理旧企业微信登录状态') }
  }

  let previousSlot: string | null
  try {
    previousSlot = (await bridgeClient.getCredentialSlot()).credentialSlot
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法读取当前企业微信连接') }
  }

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
    await bridgeClient.validateConnection(outcome.cookieJar, formId, slot)
  } catch (error) {
    try {
      await credentialStore.deleteEventually(slot)
    } catch {
      return {
        status: 'failed',
        reason: `${toReason(error, '连接校验失败')}；且无法清理本次登录状态，请检查本机数据目录权限`
      }
    }
    return { status: 'failed', reason: toReason(error, '连接校验失败') }
  }

  // The old slot is resolved through the current user's double-authenticated
  // Main-only binding, so reconnect cleanup also works after an app restart.
  if (previousSlot !== null && previousSlot !== slot) {
    try {
      await credentialStore.deleteEventually(previousSlot)
    } catch {
      return {
        status: 'connected',
        reason: '企业微信已连接，但无法清理旧登录状态，请检查本机数据目录权限'
      }
    }
  }
  return { status: 'connected', reason: null }
}

async function disconnect(
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient
): Promise<WeComDisconnectResult> {
  try {
    await credentialStore.retryPendingDeletes()
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法清理旧企业微信登录状态') }
  }

  let slot: string | null
  try {
    slot = (await bridgeClient.getCredentialSlot()).credentialSlot
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法读取当前企业微信连接') }
  }
  let cookieJar: WeComCookie[] | null = null
  if (slot !== null) {
    try {
      cookieJar = await credentialStore.load(slot)
      if (cookieJar === null) {
        // The local state is already absent. Still ask the backend to heal its
        // binding, but do not perform another irreversible local operation.
      } else {
        await credentialStore.delete(slot)
      }
    } catch (error) {
      return { status: 'failed', reason: toReason(error, '无法清除企业微信登录状态') }
    }
  }

  try {
    await bridgeClient.disconnect()
  } catch (error) {
    if (slot === null) {
      return { status: 'failed', reason: toReason(error, '无法通知后端断开连接') }
    }

    let currentConnection
    try {
      currentConnection = await bridgeClient.getCredentialSlot()
    } catch {
      return {
        status: 'failed',
        reason: `${toReason(error, '无法通知后端断开连接')}；暂时无法确认后端状态，请稍后重试断开`
      }
    }

    // The backend intentionally retains the opaque slot on a disconnected
    // binding, so status (not nullability) proves that the idempotent write
    // committed and only its response was lost.
    if (currentConnection.connectionStatus === 'disconnected') {
      return { status: 'disconnected', reason: null }
    }
    if (currentConnection.credentialSlot !== slot) {
      return {
        status: 'failed',
        reason: '企业微信连接已在别处更新，请刷新后重试'
      }
    }

    // The backend still points at the exact slot we deleted, so this is a
    // definite failure and restoring the encrypted credential is safe.
    if (cookieJar !== null) {
      try {
        await credentialStore.restore(slot, cookieJar)
      } catch {
        return {
          status: 'failed',
          reason: `${toReason(error, '无法通知后端断开连接')}；且无法恢复本地登录状态，请重新连接企业微信`
        }
      }
    }
    return { status: 'failed', reason: toReason(error, '无法通知后端断开连接') }
  }
  return { status: 'disconnected', reason: null }
}

async function executeSync(
  recordId: string,
  credentialStore: WeComCredentialStore,
  bridgeClient: WeComBridgeClient
): Promise<WeComExecuteSyncResult> {
  let connection
  try {
    connection = await bridgeClient.getCredentialSlot()
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法读取当前企业微信连接') }
  }
  if (connection.credentialSlot === null || connection.connectionStatus !== 'connected') {
    return { status: 'failed', reason: '企业微信尚未连接，请先登录' }
  }
  const slot = connection.credentialSlot

  let cookieJar
  try {
    cookieJar = await credentialStore.load(slot)
  } catch (error) {
    return { status: 'failed', reason: toReason(error, '无法读取企业微信登录状态') }
  }
  if (cookieJar === null) {
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
  bridgeClient: WeComBridgeClient
): () => void {
  let connectInFlight = false
  ipcMain.handle(
    IPC_CHANNELS.WECOM_CONNECT,
    async (event, formId: unknown): Promise<WeComConnectResult> => {
      assertTrustedSender(event, window)
      if (!isValidFormId(formId)) {
        throw new Error('rejected invalid form id payload')
      }
      if (connectInFlight) {
        return { status: 'failed', reason: '企业微信登录窗口已打开' }
      }
      connectInFlight = true
      try {
        return await connect(formId.trim(), authWindowController, credentialStore, bridgeClient)
      } finally {
        connectInFlight = false
      }
    }
  )

  ipcMain.handle(IPC_CHANNELS.WECOM_DISCONNECT, async (event): Promise<WeComDisconnectResult> => {
    assertTrustedSender(event, window)
    return disconnect(credentialStore, bridgeClient)
  })

  ipcMain.handle(
    IPC_CHANNELS.WECOM_EXECUTE_SYNC,
    async (event, recordId: unknown): Promise<WeComExecuteSyncResult> => {
      assertTrustedSender(event, window)
      if (typeof recordId !== 'string' || !ULID_PATTERN.test(recordId)) {
        throw new Error('rejected invalid record id payload')
      }
      return executeSync(recordId, credentialStore, bridgeClient)
    }
  )

  return () => {
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_CONNECT)
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_DISCONNECT)
    ipcMain.removeHandler(IPC_CHANNELS.WECOM_EXECUTE_SYNC)
  }
}

import { describe, expect, it, vi } from 'vitest'

import type { WeComCookie } from '../../security/wecom-credential-store'
import {
  isAllowedWeComNavigationUrl,
  pollForWeComLogin,
  toWeComCookie,
  WeComAuthWindowController,
  type WeComAuthSession,
  type WeComAuthSessionHandle,
  type WeComAuthWindow
} from '../auth-window-controller'
import { WECOM_AUTH_WEB_PREFERENCES, WECOM_LOGIN_MARKER_COOKIE_NAME } from '../constants'

function cookie(overrides: Partial<WeComCookie> = {}): WeComCookie {
  return {
    name: WECOM_LOGIN_MARKER_COOKIE_NAME,
    value: 'session-value',
    domain: 'doc.weixin.qq.com',
    path: '/',
    secure: true,
    httpOnly: true,
    sameSite: 'lax',
    expirationDate: 1_999_999_999,
    ...overrides
  }
}

describe('isAllowedWeComNavigationUrl', () => {
  it('allows the documented WeCom official hosts over https', () => {
    expect(isAllowedWeComNavigationUrl('https://doc.weixin.qq.com/some/path')).toBe(true)
    expect(isAllowedWeComNavigationUrl('https://work.weixin.qq.com/login')).toBe(true)
  })

  it('rejects http (non-https) even for an allowed host', () => {
    expect(isAllowedWeComNavigationUrl('http://doc.weixin.qq.com/')).toBe(false)
  })

  it('rejects unrelated hosts', () => {
    expect(isAllowedWeComNavigationUrl('https://evil.example.com/')).toBe(false)
  })

  it('rejects lookalike hosts that merely contain the allowed hostname', () => {
    expect(isAllowedWeComNavigationUrl('https://doc.weixin.qq.com.evil.com/')).toBe(false)
    expect(isAllowedWeComNavigationUrl('https://evil.com/doc.weixin.qq.com')).toBe(false)
  })

  it('rejects malformed URLs instead of throwing', () => {
    expect(isAllowedWeComNavigationUrl('not-a-url')).toBe(false)
  })
})

describe('WECOM_AUTH_WEB_PREFERENCES', () => {
  it('is the exact, minimal safe webPreferences with no preload script', () => {
    expect(WECOM_AUTH_WEB_PREFERENCES).toEqual({
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false
    })
    expect(Object.prototype.hasOwnProperty.call(WECOM_AUTH_WEB_PREFERENCES, 'preload')).toBe(false)
  })
})

describe('toWeComCookie', () => {
  it('normalizes an unknown/missing sameSite to unspecified', () => {
    expect(
      toWeComCookie({
        name: 'a',
        value: 'b',
        domain: 'doc.weixin.qq.com',
        path: '/',
        secure: true,
        httpOnly: true
      }).sameSite
    ).toBe('unspecified')
  })

  it('passes through recognized sameSite values', () => {
    expect(
      toWeComCookie({
        name: 'a',
        value: 'b',
        domain: 'doc.weixin.qq.com',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'strict'
      }).sameSite
    ).toBe('strict')
  })

  it('defaults a missing expirationDate to null (session cookie)', () => {
    expect(
      toWeComCookie({
        name: 'a',
        value: 'b',
        domain: 'doc.weixin.qq.com',
        path: '/',
        secure: true,
        httpOnly: true
      }).expirationDate
    ).toBeNull()
  })
})

function emptySession(): WeComAuthSession {
  return {
    cookies: { get: vi.fn(async () => []) }
  }
}

describe('pollForWeComLogin', () => {
  it('resolves success with the full cookie jar once the marker cookie appears', async () => {
    let markerCalls = 0
    const fullJar = [cookie(), cookie({ name: 'TOK', value: 'tok' })]
    const session: WeComAuthSession = {
      cookies: {
        get: vi.fn(async (filter: { name?: string }) => {
          if (filter.name === WECOM_LOGIN_MARKER_COOKIE_NAME) {
            markerCalls += 1
            return markerCalls >= 2 ? [cookie()] : []
          }
          return fullJar
        })
      }
    }

    const outcome = await pollForWeComLogin(session, {
      timeoutMs: 5_000,
      pollIntervalMs: 10,
      sleep: async () => {}
    })

    expect(outcome).toEqual({ status: 'success', cookieJar: fullJar })
  })

  it('treats a present-but-empty marker cookie as not yet logged in', async () => {
    let markerCalls = 0
    const session: WeComAuthSession = {
      cookies: {
        get: vi.fn(async (filter: { name?: string }) => {
          if (filter.name === WECOM_LOGIN_MARKER_COOKIE_NAME) {
            markerCalls += 1
            return [cookie({ value: '' })]
          }
          return []
        })
      }
    }

    const outcome = await pollForWeComLogin(session, {
      timeoutMs: 20,
      pollIntervalMs: 10,
      now: (() => {
        let clock = 0
        return () => {
          clock += 5
          return clock
        }
      })(),
      sleep: async () => {}
    })

    expect(outcome.status).toBe('timeout')
    expect(markerCalls).toBeGreaterThan(0)
  })

  it('resolves timeout when the marker cookie never appears before the deadline', async () => {
    const session = emptySession()
    let clock = 0

    const outcome = await pollForWeComLogin(session, {
      timeoutMs: 30,
      pollIntervalMs: 10,
      now: () => clock,
      sleep: async () => {
        clock += 10
      }
    })

    expect(outcome).toEqual({ status: 'timeout' })
  })

  it('resolves canceled as soon as the cancellation signal is set, without waiting out the timeout', async () => {
    const session = emptySession()

    const outcome = await pollForWeComLogin(session, {
      timeoutMs: 60_000,
      pollIntervalMs: 10,
      isCanceled: () => true
    })

    expect(outcome).toEqual({ status: 'canceled' })
  })
})

interface FakeWindowHandle {
  window: WeComAuthWindow
  loadURL: ReturnType<typeof vi.fn>
  close: ReturnType<typeof vi.fn>
  triggerClosed: () => void
}

function fakeWindow(loadURLImpl?: () => Promise<void>): FakeWindowHandle {
  let destroyed = false
  let closedListener: (() => void) | null = null
  const close = vi.fn(() => {
    destroyed = true
    closedListener?.()
  })
  const loadURL = vi.fn(loadURLImpl ?? (async () => {}))
  const window: WeComAuthWindow = {
    loadURL,
    isDestroyed: () => destroyed,
    close,
    on: (_event, listener) => {
      closedListener = listener
    }
  }
  return { window, loadURL, close, triggerClosed: () => closedListener?.() }
}

function fakeSessionHandle(cookieJar: WeComCookie[] = []): {
  handle: WeComAuthSessionHandle
  clearStorageData: ReturnType<typeof vi.fn>
} {
  const clearStorageData = vi.fn(async () => {})
  const handle: WeComAuthSessionHandle = {
    cookies: { get: vi.fn(async () => cookieJar) },
    clearStorageData
  }
  return { handle, clearStorageData }
}

describe('WeComAuthWindowController', () => {
  it('returns success with the cookie jar and tears down the window/session', async () => {
    const jar = [cookie()]
    const { handle, clearStorageData } = fakeSessionHandle(jar)
    const { window, close } = fakeWindow()

    const controller = new WeComAuthWindowController({
      createSession: () => handle,
      createWindow: () => window,
      timeoutMs: 1_000,
      pollIntervalMs: 5,
      sleep: async () => {}
    })

    const outcome = await controller.connect()

    expect(outcome).toEqual({ status: 'success', cookieJar: jar })
    expect(close).toHaveBeenCalledTimes(1)
    expect(clearStorageData).toHaveBeenCalledTimes(1)
  })

  it('uses a distinct, non-persist partition name on each call', async () => {
    const partitions: string[] = []
    const controller = new WeComAuthWindowController({
      createSession: (partition) => {
        partitions.push(partition)
        return fakeSessionHandle([cookie()]).handle
      },
      createWindow: () => fakeWindow().window,
      timeoutMs: 1_000,
      pollIntervalMs: 5,
      sleep: async () => {}
    })

    await Promise.all([controller.connect(), controller.connect()])

    expect(partitions).toHaveLength(2)
    expect(partitions[0]).not.toBe(partitions[1])
    for (const partition of partitions) {
      expect(partition.startsWith('wecom-auth-')).toBe(true)
      expect(partition.startsWith('persist:')).toBe(false)
    }
  })

  it('reports a clean failure (and still tears down) when the window fails to load', async () => {
    const { handle, clearStorageData } = fakeSessionHandle()
    const { window, close } = fakeWindow(async () => {
      throw new Error('net::ERR_FAILED')
    })

    const controller = new WeComAuthWindowController({
      createSession: () => handle,
      createWindow: () => window
    })

    const outcome = await controller.connect()

    expect(outcome).toEqual({ status: 'failed', reason: 'net::ERR_FAILED' })
    expect(close).toHaveBeenCalledTimes(1)
    expect(clearStorageData).toHaveBeenCalledTimes(1)
  })

  it('resolves canceled when cancel() is called mid-login and closes the window', async () => {
    const { handle } = fakeSessionHandle()
    const { window, close } = fakeWindow()

    const controller = new WeComAuthWindowController({
      createSession: () => handle,
      createWindow: () => window,
      timeoutMs: 60_000,
      pollIntervalMs: 5,
      sleep: async () => {}
    })

    const connectPromise = controller.connect()
    // give connect() a tick to install the closed-listener before canceling
    await Promise.resolve()
    controller.cancel()

    const outcome = await connectPromise
    expect(outcome).toEqual({ status: 'canceled' })
    expect(close).toHaveBeenCalled()
  })

  it('treats the user closing the login window as a cancellation', async () => {
    const { handle } = fakeSessionHandle()
    const { window, triggerClosed } = fakeWindow()

    const controller = new WeComAuthWindowController({
      createSession: () => handle,
      createWindow: () => window,
      timeoutMs: 60_000,
      pollIntervalMs: 5,
      sleep: async () => {}
    })

    const connectPromise = controller.connect()
    await Promise.resolve()
    triggerClosed()

    const outcome = await connectPromise
    expect(outcome).toEqual({ status: 'canceled' })
  })
})

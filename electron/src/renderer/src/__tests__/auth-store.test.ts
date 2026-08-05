import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const authApi = vi.hoisted(() => ({
  getBootstrapStatus: vi.fn(),
  bootstrapAdmin: vi.fn(),
  login: vi.fn(),
  getMe: vi.fn(),
  changePassword: vi.fn(),
  logout: vi.fn()
}))

vi.mock('@renderer/api/auth', () => authApi)

import { ApiError } from '@renderer/api/client'
import { SecureStorageUnavailableError, useAuthStore } from '@renderer/stores/auth'
import type { UserData } from '@renderer/types/user'

const user: UserData = {
  id: '01K000000000000000000000',
  username: 'admin',
  display_name: 'Admin',
  role: 'admin',
  is_active: true,
  created_at: '2026-08-05T00:00:00+00:00'
}

function tokenBridge(options: { available?: boolean; token?: string | null } = {}): {
  get: ReturnType<typeof vi.fn>
  set: ReturnType<typeof vi.fn>
  clear: ReturnType<typeof vi.fn>
} {
  const available = options.available ?? true
  return {
    get: vi.fn().mockResolvedValue({
      available,
      token: options.token ?? null,
      reason: available ? null : 'secure-storage-unavailable'
    }),
    set: vi.fn().mockResolvedValue({
      available,
      token: null,
      reason: available ? null : 'secure-storage-unavailable'
    }),
    clear: vi.fn().mockResolvedValue({
      available,
      token: null,
      reason: available ? null : 'secure-storage-unavailable'
    })
  }
}

function stubWindow(token = tokenBridge()): ReturnType<typeof tokenBridge> {
  vi.stubGlobal('window', {
    runtimeBridge: {
      token,
      api: { getConfig: vi.fn() },
      sidecar: { getStatus: vi.fn(), onStatusChange: vi.fn(), retry: vi.fn() }
    }
  })
  return token
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    authApi.getBootstrapStatus.mockResolvedValue({ initialized: true })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('restores a safeStorage token into memory and verifies it with /auth/me', async () => {
    const bridge = stubWindow(tokenBridge({ token: 'saved.jwt.token' }))
    authApi.getMe.mockResolvedValue(user)
    const store = useAuthStore()

    await store.initialize()

    expect(bridge.get).toHaveBeenCalledOnce()
    expect(store.accessToken).toBe('saved.jwt.token')
    expect(store.currentUser).toEqual(user)
    expect(store.isAuthenticated).toBe(true)
  })

  it('clears an expired restored token without exposing it to ordinary storage', async () => {
    const bridge = stubWindow(tokenBridge({ token: 'expired.jwt.token' }))
    authApi.getMe.mockRejectedValue(new ApiError(40102, 'Token 无效或已过期', 401))
    const store = useAuthStore()

    await store.initialize()

    expect(bridge.clear).toHaveBeenCalledOnce()
    expect(store.accessToken).toBeNull()
    expect(store.currentUser).toBeNull()
  })

  it('clears a stale token when the current database still requires bootstrap', async () => {
    authApi.getBootstrapStatus.mockResolvedValue({ initialized: false })
    const bridge = stubWindow(tokenBridge({ token: 'stale.jwt.token' }))
    const store = useAuthStore()

    await store.initialize()

    expect(bridge.clear).toHaveBeenCalledOnce()
    expect(store.systemInitialized).toBe(false)
    expect(store.accessToken).toBeNull()
    expect(authApi.getMe).not.toHaveBeenCalled()
  })

  it('refuses login when safeStorage encryption is unavailable', async () => {
    stubWindow(tokenBridge({ available: false }))
    const store = useAuthStore()
    await store.initialize()

    await expect(store.login('admin', 'password')).rejects.toBeInstanceOf(
      SecureStorageUnavailableError
    )
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('persists a successful login through the token bridge and keeps only an in-memory copy', async () => {
    const bridge = stubWindow()
    authApi.login.mockResolvedValue({
      access_token: 'new.jwt.token',
      expires_at: '2026-08-06T00:00:00+00:00'
    })
    authApi.getMe.mockResolvedValue(user)
    const store = useAuthStore()
    await store.initialize()

    await store.login('admin', 'password')

    expect(bridge.set).toHaveBeenCalledWith('new.jwt.token')
    expect(store.accessToken).toBe('new.jwt.token')
    expect(store.currentUser).toEqual(user)
  })

  it('clears the local session after a password change', async () => {
    const bridge = stubWindow()
    authApi.changePassword.mockResolvedValue({})
    const store = useAuthStore()
    store.accessToken = 'old.jwt.token'
    store.currentUser = user

    await store.changePassword('old password', 'new password')

    expect(bridge.clear).toHaveBeenCalledOnce()
    expect(store.accessToken).toBeNull()
    expect(store.currentUser).toBeNull()
  })
})

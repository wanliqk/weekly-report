import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const axiosMock = vi.hoisted(() => {
  let requestInterceptor: ((config: { headers: Record<string, string> }) => unknown) | null = null
  const request = vi.fn()
  return {
    request,
    create: vi.fn(() => ({
      interceptors: {
        request: {
          use: vi.fn((handler: typeof requestInterceptor) => {
            requestInterceptor = handler
          })
        }
      },
      request: vi.fn(async (config: { headers?: Record<string, string> }) => {
        const prepared = { ...config, headers: { ...(config.headers ?? {}) } }
        requestInterceptor?.(prepared)
        return request(prepared)
      })
    })),
    isAxiosError: vi.fn((error: unknown) =>
      Boolean(typeof error === 'object' && error !== null && '__axios' in error)
    ),
    reset: () => {
      requestInterceptor = null
      request.mockReset()
    }
  }
})

vi.mock('axios', () => ({
  default: { create: axiosMock.create, isAxiosError: axiosMock.isAxiosError }
}))

import { configureApiAuth, requestData, resetApiClient } from '@renderer/api/client'

describe('API client authentication', () => {
  beforeEach(() => {
    axiosMock.reset()
    axiosMock.create.mockClear()
    resetApiClient()
    vi.stubGlobal('window', {
      runtimeBridge: {
        api: {
          getConfig: vi.fn().mockResolvedValue({
            baseUrl: 'http://127.0.0.1:1234',
            runtimeSecretHeader: 'X-Runtime-Secret',
            runtimeSecret: 'runtime-secret'
          })
        }
      }
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('adds the in-memory bearer token alongside the runtime secret', async () => {
    configureApiAuth({ getAccessToken: () => 'access-token', onTokenInvalid: vi.fn() })
    axiosMock.request.mockResolvedValue({
      status: 200,
      data: { code: 0, msg: 'success', data: { ok: true } }
    })

    await expect(requestData<{ ok: boolean }>({ method: 'GET', url: '/probe' })).resolves.toEqual({
      ok: true
    })
    expect(axiosMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: { 'X-Runtime-Secret': 'runtime-secret' }
      })
    )
    expect(axiosMock.request).toHaveBeenCalledWith(
      expect.objectContaining({ headers: { Authorization: 'Bearer access-token' } })
    )
  })

  it('invokes the token-invalid callback for a 40102 response', async () => {
    const onTokenInvalid = vi.fn()
    configureApiAuth({ getAccessToken: () => 'expired-token', onTokenInvalid })
    axiosMock.request.mockRejectedValue({
      __axios: true,
      response: {
        status: 401,
        data: { code: 40102, msg: 'Token 无效或已过期', data: {} }
      }
    })

    await expect(requestData({ method: 'GET', url: '/probe' })).rejects.toHaveProperty(
      'code',
      40102
    )
    expect(onTokenInvalid).toHaveBeenCalledOnce()
  })
})

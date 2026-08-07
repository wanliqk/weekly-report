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

import { configureApiAuth, requestBinary, requestData, resetApiClient } from '@renderer/api/client'

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
    configureApiAuth({
      getAccessToken: () => 'access-token',
      onTokenInvalid: vi.fn(),
      onPasswordChangeRequired: vi.fn()
    })
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
    configureApiAuth({
      getAccessToken: () => 'expired-token',
      onTokenInvalid,
      onPasswordChangeRequired: vi.fn()
    })
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

  it('invokes the password-change-required callback for a 40303 response', async () => {
    const onPasswordChangeRequired = vi.fn()
    configureApiAuth({
      getAccessToken: () => 'temp-password-token',
      onTokenInvalid: vi.fn(),
      onPasswordChangeRequired
    })
    axiosMock.request.mockRejectedValue({
      __axios: true,
      response: {
        status: 403,
        data: { code: 40303, msg: '请先修改临时密码', data: {} }
      }
    })

    await expect(requestData({ method: 'GET', url: '/probe' })).rejects.toHaveProperty(
      'code',
      40303
    )
    expect(onPasswordChangeRequired).toHaveBeenCalledOnce()
  })

  it('returns the raw bytes and file name for a binary download', async () => {
    configureApiAuth({
      getAccessToken: () => 'access-token',
      onTokenInvalid: vi.fn(),
      onPasswordChangeRequired: vi.fn()
    })
    const bytes = new Uint8Array([1, 2, 3]).buffer
    axiosMock.request.mockResolvedValue({
      status: 200,
      data: bytes,
      headers: { 'content-disposition': 'attachment; filename="report.xlsx"' }
    })

    const result = await requestBinary({ method: 'GET', url: '/probe/file' })

    expect(result.data).toBe(bytes)
    expect(result.fileName).toBe('report.xlsx')
  })

  it('prefers the RFC 6266 UTF-8 file name over the ASCII fallback', async () => {
    configureApiAuth({
      getAccessToken: () => 'access-token',
      onTokenInvalid: vi.fn(),
      onPasswordChangeRequired: vi.fn()
    })
    const bytes = new Uint8Array([1, 2, 3]).buffer
    axiosMock.request.mockResolvedValue({
      status: 200,
      data: bytes,
      headers: {
        'content-disposition':
          'attachment; filename="daily-report-export.xlsx"; filename*=UTF-8\'\'%E6%97%A5%E6%8A%A5-Alice_2026%E5%B9%B48%E6%9C%887%E6%97%A5.xlsx'
      }
    })

    const result = await requestBinary({ method: 'GET', url: '/probe/file' })

    expect(result.fileName).toBe('日报-Alice_2026年8月7日.xlsx')
  })

  it('decodes a JSON error body returned as an ArrayBuffer into the real business code', async () => {
    configureApiAuth({
      getAccessToken: () => 'access-token',
      onTokenInvalid: vi.fn(),
      onPasswordChangeRequired: vi.fn()
    })
    const errorBody = new TextEncoder().encode(
      JSON.stringify({ code: 40401, msg: '导出任务不存在', data: {} })
    ).buffer
    axiosMock.request.mockRejectedValue({
      __axios: true,
      response: { status: 404, data: errorBody }
    })

    await expect(requestBinary({ method: 'GET', url: '/probe/file' })).rejects.toHaveProperty(
      'code',
      40401
    )
  })
})

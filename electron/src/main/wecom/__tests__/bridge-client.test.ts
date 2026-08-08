import { describe, expect, it, vi } from 'vitest'

import { MAIN_BRIDGE_SECRET_HEADER } from '../../../shared/contracts'
import type { WeComCookie } from '../../security/wecom-credential-store'
import { WeComBridgeClient, WeComBridgeClientError, type WeComFetch } from '../bridge-client'

function sampleCookieJar(): WeComCookie[] {
  return [
    {
      name: 'wedoc_sid',
      value: 'session-value',
      domain: 'doc.weixin.qq.com',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'lax',
      expirationDate: 1_999_999_999
    }
  ]
}

function jsonResponse(body: unknown, init: { ok: boolean; status: number }): Response {
  return {
    ok: init.ok,
    status: init.status,
    json: async () => body
  } as unknown as Response
}

function baseDeps(fetchImpl: WeComFetch): {
  getBaseUrl: () => string | null
  getMainBridgeSecret: () => string | null
  getAccessToken: () => Promise<string | null>
  fetchImpl: WeComFetch
} {
  return {
    getBaseUrl: () => 'http://127.0.0.1:54321',
    getMainBridgeSecret: () => 'the-bridge-secret',
    getAccessToken: async () => 'the-jwt',
    fetchImpl
  }
}

describe('WeComBridgeClient', () => {
  it('validateConnection posts the expected URL, headers, and body', async () => {
    const fetchImpl = vi
      .fn<WeComFetch>()
      .mockResolvedValue(jsonResponse({}, { ok: true, status: 200 }))
    const client = new WeComBridgeClient(baseDeps(fetchImpl))

    await client.validateConnection(sampleCookieJar(), 'form-123')

    expect(fetchImpl).toHaveBeenCalledTimes(1)
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://127.0.0.1:54321/api/v1/internal/wecom/connections/validate')
    expect(init.method).toBe('POST')
    const headers = init.headers as Record<string, string>
    expect(headers[MAIN_BRIDGE_SECRET_HEADER]).toBe('the-bridge-secret')
    expect(headers.Authorization).toBe('Bearer the-jwt')
    const body = JSON.parse(init.body as string) as { form_id: string; cookie_jar: unknown[] }
    expect(body.form_id).toBe('form-123')
    expect(body.cookie_jar).toEqual([
      {
        name: 'wedoc_sid',
        value: 'session-value',
        domain: 'doc.weixin.qq.com',
        path: '/',
        secure: true,
        http_only: true,
        same_site: 'lax',
        expiration_date: 1_999_999_999
      }
    ])
  })

  it('executeSync posts to the record-scoped execute path with the cookie jar', async () => {
    const fetchImpl = vi
      .fn<WeComFetch>()
      .mockResolvedValue(jsonResponse({}, { ok: true, status: 200 }))
    const client = new WeComBridgeClient(baseDeps(fetchImpl))

    await client.executeSync('01ARZ3NDEKTSV4RRFFQ69G5FAV', sampleCookieJar())

    const [url] = fetchImpl.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(
      'http://127.0.0.1:54321/api/v1/internal/wecom/sync-records/01ARZ3NDEKTSV4RRFFQ69G5FAV/execute'
    )
  })

  it('disconnect posts to the disconnect path with an empty body', async () => {
    const fetchImpl = vi
      .fn<WeComFetch>()
      .mockResolvedValue(jsonResponse({}, { ok: true, status: 200 }))
    const client = new WeComBridgeClient(baseDeps(fetchImpl))

    await client.disconnect()

    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://127.0.0.1:54321/api/v1/internal/wecom/connections/disconnect')
    expect(JSON.parse(init.body as string)).toEqual({})
  })

  it('turns a 404 (endpoint not implemented yet) into a clean typed error, not a raw exception', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ detail: 'Not Found' }, { ok: false, status: 404 })
    )
    const client = new WeComBridgeClient(baseDeps(fetchImpl))

    await expect(client.validateConnection(sampleCookieJar(), 'form-123')).rejects.toBeInstanceOf(
      WeComBridgeClientError
    )
  })

  it('turns a network-level fetch failure into a clean typed error', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('ECONNREFUSED')
    })
    const client = new WeComBridgeClient(baseDeps(fetchImpl))

    await expect(client.disconnect()).rejects.toBeInstanceOf(WeComBridgeClientError)
  })

  it('refuses to call out when the sidecar is not ready, without invoking fetch', async () => {
    const fetchImpl = vi.fn()
    const client = new WeComBridgeClient({
      getBaseUrl: () => null,
      getMainBridgeSecret: () => 'the-bridge-secret',
      getAccessToken: async () => 'the-jwt',
      fetchImpl
    })

    await expect(client.disconnect()).rejects.toBeInstanceOf(WeComBridgeClientError)
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('refuses to call out when the main bridge secret is unavailable, without invoking fetch', async () => {
    const fetchImpl = vi.fn()
    const client = new WeComBridgeClient({
      getBaseUrl: () => 'http://127.0.0.1:54321',
      getMainBridgeSecret: () => null,
      getAccessToken: async () => 'the-jwt',
      fetchImpl
    })

    await expect(client.disconnect()).rejects.toBeInstanceOf(WeComBridgeClientError)
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('refuses to call out when there is no current access token, without invoking fetch', async () => {
    const fetchImpl = vi.fn()
    const client = new WeComBridgeClient({
      getBaseUrl: () => 'http://127.0.0.1:54321',
      getMainBridgeSecret: () => 'the-bridge-secret',
      getAccessToken: async () => null,
      fetchImpl
    })

    await expect(client.disconnect()).rejects.toBeInstanceOf(WeComBridgeClientError)
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('rejects a non-loopback base URL instead of calling out to it', async () => {
    const fetchImpl = vi.fn()
    const client = new WeComBridgeClient({
      getBaseUrl: () => 'https://not-loopback.example.com',
      getMainBridgeSecret: () => 'the-bridge-secret',
      getAccessToken: async () => 'the-jwt',
      fetchImpl
    })

    await expect(client.disconnect()).rejects.toBeInstanceOf(WeComBridgeClientError)
    expect(fetchImpl).not.toHaveBeenCalled()
  })
})

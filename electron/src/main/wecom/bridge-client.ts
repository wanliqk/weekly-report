import { MAIN_BRIDGE_SECRET_HEADER } from '../../shared/contracts'
import type { WeComCookie } from '../security/wecom-credential-store'

export class WeComBridgeClientError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'WeComBridgeClientError'
  }
}

export interface WeComValidateConnectionResult {
  status: 'connected'
}

export interface WeComExecuteSyncBridgeResult {
  status: 'submitted'
}

export interface WeComDisconnectBridgeResult {
  status: 'disconnected'
}

export type WeComFetch = typeof fetch

export interface WeComBridgeClientDeps {
  /** Current sidecar base URL (`http://127.0.0.1:<port>`), or `null` while the
   * sidecar isn't ready. Callers pass `SidecarManager.getRuntimeConfig()?.baseUrl`. */
  getBaseUrl: () => string | null
  /** Main-only bridge secret (SEC-014). Callers pass `SidecarManager.getMainBridgeSecret()`. */
  getMainBridgeSecret: () => string | null
  /** Current user's JWT, read from `SecureTokenStore` — never renderer-supplied. */
  getAccessToken: () => Promise<string | null>
  fetchImpl?: WeComFetch
}

// The sidecar only ever announces `http://127.0.0.1:<port>` (see
// `SidecarManager.doStart()`); requiring an exact loopback match here is
// defense in depth against `WeComBridgeClient` ever being pointed at a
// non-loopback host (docs/方案设计.md §4.1: "校验回环地址").
const LOOPBACK_BASE_URL_PATTERN = /^http:\/\/(?:127\.0\.0\.1|localhost):\d+$/

/**
 * Thin Main-only bridge to the FastAPI `/api/v1/internal/wecom/**` endpoints
 * (docs/方案设计.md §9.2). Those endpoints don't exist until WECOM-06, so every
 * call made against a real sidecar today will 404 — that's expected for this
 * task. This class's only job is to shape each request correctly (loopback
 * base URL, `X-Main-Bridge-Secret` + `Authorization` headers, structured JSON
 * body — never a raw `Cookie` header or an arbitrary target URL, per §9.2/§9.3)
 * and turn any failure into a single clean `WeComBridgeClientError` instead of
 * letting a raw network exception or an unhandled 404 reach IPC callers.
 */
export class WeComBridgeClient {
  constructor(private readonly deps: WeComBridgeClientDeps) {}

  async validateConnection(
    cookieJar: WeComCookie[],
    formId: string
  ): Promise<WeComValidateConnectionResult> {
    await this.post('/api/v1/internal/wecom/connections/validate', {
      cookie_jar: serializeCookieJar(cookieJar),
      form_id: formId
    })
    return { status: 'connected' }
  }

  async executeSync(
    recordId: string,
    cookieJar: WeComCookie[]
  ): Promise<WeComExecuteSyncBridgeResult> {
    await this.post(`/api/v1/internal/wecom/sync-records/${encodeURIComponent(recordId)}/execute`, {
      cookie_jar: serializeCookieJar(cookieJar)
    })
    return { status: 'submitted' }
  }

  async disconnect(): Promise<WeComDisconnectBridgeResult> {
    await this.post('/api/v1/internal/wecom/connections/disconnect', {})
    return { status: 'disconnected' }
  }

  private async post(path: string, body: unknown): Promise<unknown> {
    const baseUrl = this.deps.getBaseUrl()
    if (baseUrl === null || !LOOPBACK_BASE_URL_PATTERN.test(baseUrl)) {
      throw new WeComBridgeClientError('企业微信内部服务尚未就绪')
    }
    const mainBridgeSecret = this.deps.getMainBridgeSecret()
    if (mainBridgeSecret === null) {
      throw new WeComBridgeClientError('企业微信内部服务尚未就绪')
    }
    const accessToken = await this.deps.getAccessToken()
    if (accessToken === null) {
      throw new WeComBridgeClientError('登录状态无效，请重新登录')
    }

    const fetchImpl = this.deps.fetchImpl ?? fetch
    let response: Response
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          [MAIN_BRIDGE_SECRET_HEADER]: mainBridgeSecret,
          Authorization: `Bearer ${accessToken}`
        },
        body: JSON.stringify(body)
      })
    } catch {
      throw new WeComBridgeClientError('无法连接企业微信内部服务')
    }

    if (!response.ok) {
      throw new WeComBridgeClientError(`企业微信内部服务请求失败（HTTP ${response.status}）`)
    }

    try {
      return await response.json()
    } catch {
      throw new WeComBridgeClientError('企业微信内部服务返回了无法解析的响应')
    }
  }
}

function serializeCookieJar(cookieJar: WeComCookie[]): unknown[] {
  return cookieJar.map((cookie) => ({
    name: cookie.name,
    value: cookie.value,
    domain: cookie.domain,
    path: cookie.path,
    secure: cookie.secure,
    http_only: cookie.httpOnly,
    same_site: cookie.sameSite,
    expiration_date: cookie.expirationDate
  }))
}

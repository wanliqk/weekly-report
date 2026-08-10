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

export interface WeComCredentialSlotBridgeResult {
  credentialSlot: string | null
  connectionStatus: 'connected' | 'expired' | 'disconnected' | null
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
const CREDENTIAL_SLOT_PATTERN = /^[0-9a-f]{32}$/

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/**
 * Thin Main-only bridge to the FastAPI `/api/v1/internal/wecom/**` endpoints
 * (docs/方案设计.md §9.2, implemented by `WECOM-06`). This class's only job is
 * to shape each request correctly (loopback base URL, `X-Main-Bridge-Secret` +
 * `Authorization` headers, structured JSON body — never a raw `Cookie` header
 * or an arbitrary target URL, per §9.2/§9.3) and turn any failure into a
 * single clean `WeComBridgeClientError` instead of letting a raw network
 * exception or an unhandled non-2xx response reach IPC callers.
 */
export class WeComBridgeClient {
  constructor(private readonly deps: WeComBridgeClientDeps) {}

  async getCredentialSlot(): Promise<WeComCredentialSlotBridgeResult> {
    const response = await this.request('/api/v1/internal/wecom/connections/credential-slot', 'GET')
    if (!isRecord(response) || !isRecord(response.data)) {
      throw new WeComBridgeClientError('企业微信内部服务返回了无法解析的响应')
    }
    const slot = response.data.credential_slot
    const status = response.data.connection_status
    if (slot !== null && (typeof slot !== 'string' || !CREDENTIAL_SLOT_PATTERN.test(slot))) {
      throw new WeComBridgeClientError('企业微信登录状态无效，请重新连接')
    }
    if (
      status !== null &&
      status !== 'connected' &&
      status !== 'expired' &&
      status !== 'disconnected'
    ) {
      throw new WeComBridgeClientError('企业微信连接状态无效，请重新连接')
    }
    if ((slot === null) !== (status === null)) {
      throw new WeComBridgeClientError('企业微信连接状态不完整，请重新连接')
    }
    return { credentialSlot: slot, connectionStatus: status }
  }

  async validateConnection(
    cookieJar: WeComCookie[],
    formId: string,
    credentialSlot: string
  ): Promise<WeComValidateConnectionResult> {
    await this.post('/api/v1/internal/wecom/connections/validate', {
      cookie_jar: serializeCookieJar(cookieJar),
      form_id: formId,
      credential_slot: credentialSlot
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
    return this.request(path, 'POST', body)
  }

  private async request(path: string, method: 'GET' | 'POST', body?: unknown): Promise<unknown> {
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
      const headers: Record<string, string> = {
        [MAIN_BRIDGE_SECRET_HEADER]: mainBridgeSecret,
        Authorization: `Bearer ${accessToken}`
      }
      if (method === 'POST') {
        headers['Content-Type'] = 'application/json'
      }
      response = await fetchImpl(`${baseUrl}${path}`, {
        method,
        headers,
        ...(method === 'POST' ? { body: JSON.stringify(body) } : {})
      })
    } catch {
      throw new WeComBridgeClientError('无法连接企业微信内部服务')
    }

    if (!response.ok) {
      throw new WeComBridgeClientError(await this.extractErrorMessage(response))
    }

    try {
      return await response.json()
    } catch {
      throw new WeComBridgeClientError('企业微信内部服务返回了无法解析的响应')
    }
  }

  // The sidecar's unified `{code,msg,data}` envelope (`app/core/errors.py`)
  // puts the actual, specific reason in `msg` even on a non-2xx response
  // (e.g. "企业微信模板结构已变化" for a 502) — showing only the HTTP status
  // discarded that and left the user with an undiagnosable "HTTP 502". Falls
  // back to the generic status message only when the body genuinely isn't
  // that shape (a non-FastAPI 404, a proxy error page, etc.).
  private async extractErrorMessage(response: Response): Promise<string> {
    try {
      const body: unknown = await response.json()
      if (isRecord(body) && typeof body.msg === 'string' && body.msg.trim().length > 0) {
        return body.msg
      }
    } catch {
      // Body isn't JSON at all — fall through to the generic message below.
    }
    return `企业微信内部服务请求失败（HTTP ${response.status}）`
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

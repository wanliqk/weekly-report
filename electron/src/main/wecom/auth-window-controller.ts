import type { WeComCookie } from '../security/wecom-credential-store'
import {
  WECOM_ALLOWED_NAVIGATION_HOSTS,
  WECOM_LOGIN_ENTRY_URL,
  WECOM_LOGIN_MARKER_COOKIE_NAME,
  WECOM_LOGIN_POLL_INTERVAL_MS,
  WECOM_LOGIN_TIMEOUT_MS
} from './constants'

export type WeComLoginOutcome =
  | { status: 'success'; cookieJar: WeComCookie[] }
  | { status: 'canceled' }
  | { status: 'timeout' }
  | { status: 'failed'; reason: string }

/** Minimal cookie-read surface this module needs from an Electron `Session` — kept as
 * our own interface (not `import type { Session } from 'electron'`) so this whole
 * module stays free of any value/type coupling to the `electron` package and is
 * importable under plain Vitest with a fake session, matching the pattern already
 * used by `sidecar/paths.ts`. */
export interface WeComAuthSession {
  cookies: {
    get: (filter: { name?: string; domain?: string }) => Promise<WeComCookie[]>
  }
}

export interface WeComAuthSessionHandle extends WeComAuthSession {
  clearStorageData: () => Promise<void>
}

export interface WeComAuthWindow {
  loadURL: (url: string) => Promise<void>
  isDestroyed: () => boolean
  close: () => void
  on: (event: 'closed', listener: () => void) => void
}

export interface WeComAuthWindowDeps {
  createSession: (partition: string) => WeComAuthSessionHandle
  /**
   * Receives the same `partition` string handed to `createSession`, not the
   * session handle itself — Electron's `BrowserWindow` accepts a
   * `webPreferences.partition` string directly and resolves it to the exact
   * same cached in-memory session `session.fromPartition(partition)` would
   * (real Electron sessions are cached by partition key), so both deps can
   * be built independently from the one partition value without threading an
   * `electron`-typed `Session` object through this framework-agnostic interface.
   */
  createWindow: (partition: string) => WeComAuthWindow
  /** Generates the random suffix of the `wecom-auth-<suffix>` partition name.
   * Deliberately *not* prefixed with `persist:` so Electron keeps it in-memory
   * only (docs/方案设计.md §4.1: "不能持久化到磁盘变成下次还能用的登录态"). */
  generatePartitionSuffix?: () => string
  timeoutMs?: number
  pollIntervalMs?: number
  now?: () => number
  sleep?: (ms: number) => Promise<void>
}

function defaultPartitionSuffix(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Polls an isolated login session until the marker cookie appears, the caller
 * cancels, or `timeoutMs` elapses — the "target page/API verified success" signal
 * docs/方案设计.md §2.2/§4.1 calls for, replacing the reference script's fixed
 * wait. Exported standalone (not a private method) so it can be unit tested with a
 * fake `WeComAuthSession` and no real Electron `BrowserWindow`/`session`.
 */
export async function pollForWeComLogin(
  session: WeComAuthSession,
  options: {
    timeoutMs: number
    pollIntervalMs: number
    now?: () => number
    sleep?: (ms: number) => Promise<void>
    isCanceled?: () => boolean
  }
): Promise<WeComLoginOutcome> {
  const now = options.now ?? Date.now
  const sleep = options.sleep ?? defaultSleep
  const isCanceled = options.isCanceled ?? ((): boolean => false)
  const deadline = now() + options.timeoutMs

  for (;;) {
    if (isCanceled()) {
      return { status: 'canceled' }
    }

    const markerCookies = await session.cookies.get({ name: WECOM_LOGIN_MARKER_COOKIE_NAME })
    const loggedIn = markerCookies.some((cookie) => cookie.value.length > 0)
    if (loggedIn) {
      const cookieJar = await session.cookies.get({})
      return { status: 'success', cookieJar }
    }

    if (now() >= deadline) {
      return { status: 'timeout' }
    }
    await sleep(options.pollIntervalMs)
  }
}

/**
 * Pure allow-list check for the login window's navigation restriction
 * (docs/方案设计.md §4.1/§12). Exact hostname match against
 * `WECOM_ALLOWED_NAVIGATION_HOSTS`, HTTPS only — no wildcard/suffix matching, so
 * `https://doc.weixin.qq.com.evil.com/` is rejected exactly like any other
 * unrelated host. Malformed URLs are treated as disallowed.
 */
export function isAllowedWeComNavigationUrl(url: string): boolean {
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return false
  }
  return parsed.protocol === 'https:' && WECOM_ALLOWED_NAVIGATION_HOSTS.includes(parsed.hostname)
}

/** Duck-typed input shape accepted by {@link toWeComCookie} — matches the fields
 * Electron's real `Cookie` structure exposes (only `name`/`value`/`sameSite` are
 * non-optional there too), without importing `electron`'s types. */
export interface RawElectronCookie {
  name: string
  value: string
  domain?: string
  path?: string
  secure?: boolean
  httpOnly?: boolean
  sameSite?: string
  expirationDate?: number
}

/** Maps a raw Electron cookie (or an equivalent plain object) to our stored shape,
 * normalizing the optional/loosely-typed fields Electron exposes into the strict
 * structure `WeComCredentialStore` persists. Used by the real `index.ts` wiring's
 * `createSession` adapter — kept here (not in `index.ts`) so it stays unit testable. */
export function toWeComCookie(cookie: RawElectronCookie): WeComCookie {
  return {
    name: cookie.name,
    value: cookie.value,
    domain: cookie.domain ?? '',
    path: cookie.path ?? '/',
    secure: cookie.secure ?? false,
    httpOnly: cookie.httpOnly ?? false,
    sameSite: normalizeSameSite(cookie.sameSite),
    expirationDate: typeof cookie.expirationDate === 'number' ? cookie.expirationDate : null
  }
}

function normalizeSameSite(value: string | undefined): WeComCookie['sameSite'] {
  return value === 'no_restriction' || value === 'lax' || value === 'strict' ? value : 'unspecified'
}

/**
 * Orchestrates one WeCom login attempt: opens an isolated login window, waits for
 * `pollForWeComLogin` to report completion/cancellation/timeout, and always tears
 * the temporary window/session down afterwards (docs/方案设计.md §4.1: "窗口关闭或
 * 凭证保存完成后清理临时存储"). All Electron-specific construction is injected via
 * `deps` — this class never imports `electron` itself, so it stays unit testable
 * with fakes; only `index.ts` supplies the real `BrowserWindow`/`session.fromPartition`
 * factories.
 */
export class WeComAuthWindowController {
  private activeWindow: WeComAuthWindow | null = null
  private canceled = false

  constructor(private readonly deps: WeComAuthWindowDeps) {}

  /** Requests cancellation of an in-flight `connect()` call and closes its window. */
  cancel(): void {
    this.canceled = true
    if (this.activeWindow && !this.activeWindow.isDestroyed()) {
      this.activeWindow.close()
    }
  }

  async connect(): Promise<WeComLoginOutcome> {
    this.canceled = false
    const generateSuffix = this.deps.generatePartitionSuffix ?? defaultPartitionSuffix
    const partition = `wecom-auth-${generateSuffix()}`
    const session = this.deps.createSession(partition)
    const window = this.deps.createWindow(partition)
    this.activeWindow = window

    let windowClosed = false
    window.on('closed', () => {
      windowClosed = true
    })

    try {
      await window.loadURL(WECOM_LOGIN_ENTRY_URL)
    } catch (error) {
      await this.cleanup(session, window)
      return {
        status: 'failed',
        reason: error instanceof Error ? error.message : '无法打开企业微信登录页面'
      }
    }

    const outcome = await pollForWeComLogin(session, {
      timeoutMs: this.deps.timeoutMs ?? WECOM_LOGIN_TIMEOUT_MS,
      pollIntervalMs: this.deps.pollIntervalMs ?? WECOM_LOGIN_POLL_INTERVAL_MS,
      now: this.deps.now,
      sleep: this.deps.sleep,
      isCanceled: () => this.canceled || windowClosed
    })

    await this.cleanup(session, window)
    return outcome
  }

  private async cleanup(session: WeComAuthSessionHandle, window: WeComAuthWindow): Promise<void> {
    this.activeWindow = null
    if (!window.isDestroyed()) {
      window.close()
    }
    try {
      await session.clearStorageData()
    } catch {
      // Best-effort hygiene only; the partition is random and in-memory, so a
      // failure here cannot leak the temporary session into a future login.
    }
  }
}

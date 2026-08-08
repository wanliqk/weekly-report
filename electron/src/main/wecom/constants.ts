/**
 * Generic entry point that triggers WeCom's own SSO/login flow (docs/方案设计.md
 * §4.1: "不要假设一个具体的表单 URL...导航到一个能触发企业微信 SSO 登录的通用入口即可，
 * 比如企业微信文档首页"). The concrete per-org form id is only known once a user
 * completes connection setup (WECOM-06/07), well outside this task's scope.
 */
export const WECOM_LOGIN_ENTRY_URL = 'https://doc.weixin.qq.com/'

/**
 * Cookie whose presence signals a completed login (docs/方案设计.md §4.1: "基于
 * 目标页面/接口校验成功...而非仅等待秒数"). `wedoc_sid` is the WeDoc session id used
 * by every documented internal endpoint (§2.4), so its (non-empty) presence in the
 * isolated auth session is a verifiable, not time-based, completion signal.
 */
export const WECOM_LOGIN_MARKER_COOKIE_NAME = 'wedoc_sid'

// Generous ceiling: real logins may require the user to scan a QR code or
// confirm on a phone, which is a human-paced action, not a network round trip.
export const WECOM_LOGIN_TIMEOUT_MS = 180_000
export const WECOM_LOGIN_POLL_INTERVAL_MS = 1_000

/**
 * Navigation allow-list for the isolated login window (docs/方案设计.md §4.1/§12):
 * "只允许停留在企业微信文档域...及登录相关的企业微信官方域"，做得比现有主窗口更严格。
 * Exact hostname match only (no wildcard/subdomain matching, no suffix checks) so a
 * lookalike host (e.g. `doc.weixin.qq.com.evil.com`) can never pass.
 */
export const WECOM_ALLOWED_NAVIGATION_HOSTS: readonly string[] = [
  'doc.weixin.qq.com',
  'open.weixin.qq.com',
  'work.weixin.qq.com'
]

/**
 * The exact `webPreferences` the login `BrowserWindow` must use (docs/方案设计.md
 * §4.1: `contextIsolation=true`、`sandbox=true`、`nodeIntegration=false`、无 preload).
 * Exported as a single frozen constant so the real window-construction code (only
 * reachable from `index.ts`, never under Vitest) and this module's unit tests read
 * the exact same object — the test proves what actually ships, not a parallel copy.
 */
export const WECOM_AUTH_WEB_PREFERENCES = Object.freeze({
  contextIsolation: true,
  sandbox: true,
  nodeIntegration: false
})

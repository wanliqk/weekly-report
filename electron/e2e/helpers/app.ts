import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { expect } from '@playwright/test'
import { _electron as electron, type ElectronApplication, type Page } from 'playwright-core'

// electron/e2e/helpers -> electron/e2e -> electron -> <repo root>
const ELECTRON_DIR = join(__dirname, '..', '..')
const REPO_ROOT = join(ELECTRON_DIR, '..')
const ELECTRON_EXECUTABLE = join(REPO_ROOT, 'node_modules', 'electron', 'dist', 'electron.exe')
const VENV_PYTHON = join(REPO_ROOT, 'backend', '.venv', 'Scripts', 'python.exe')

const DEFAULT_TIMEOUT_MS = 15_000

// Matches a real ULID-based report detail route (e.g. "#/daily/01H8...")
// but never the "#/daily/new" create-form route. `#/daily/.+` alone is a
// trap here: `/daily/new` satisfies it too, so `page.waitForURL(/#\/daily\/.+/)`
// called right after clicking "创建并填写" can resolve against the
// still-current `/daily/new` URL before the real navigation happens, handing
// the test the literal string "new" as a report id. ULIDs are 26 Crockford
// base32 characters; this pattern is a deliberately loose superset of that
// (plain `[0-9A-Z]{20,30}`) so it never has to track ULID's exact excluded
// letters, while still being nothing "new" can ever match.
export const DAILY_DETAIL_URL_PATTERN = /#\/daily\/[0-9A-Z]{20,30}$/
export const WEEKLY_DETAIL_URL_PATTERN = /#\/weekly\/[0-9A-Z]{20,30}$/

export interface LaunchedApp {
  app: ElectronApplication
  page: Page
  /** Root of this test's isolated temp dir; never the repo's real `.local-data/`. */
  dataDir: string
}

/**
 * Launches the real built Electron app (`electron/out/**`, produced by
 * `npm run build`) with a fresh, isolated data directory so no E2E run ever
 * touches the repo's own `.local-data/`. `cwd: ELECTRON_DIR` + `args: ['.']`
 * makes Electron read `electron/package.json`'s `main` and resolve
 * `app.getAppPath()` to `electron/`, which `sidecar/paths.ts`'s
 * development-mode branch depends on to find `backend/.venv/`.
 */
export async function launchApp(label: string): Promise<LaunchedApp> {
  const dataDir = mkdtempSync(join(tmpdir(), `weekly-report-e2e-${label}-`))

  const app = await electron.launch({
    executablePath: ELECTRON_EXECUTABLE,
    cwd: ELECTRON_DIR,
    args: ['.'],
    env: {
      ...process.env,
      WEEKLY_REPORT_DATA_DIR: join(dataDir, 'data'),
      WEEKLY_REPORT_LOG_DIR: join(dataDir, 'logs'),
      WEEKLY_REPORT_BACKUP_DIR: join(dataDir, 'backups'),
      WEEKLY_REPORT_EXPORT_TEMP_DIR: join(dataDir, 'temp', 'exports'),
      WEEKLY_REPORT_MANUAL_BACKUP_TEMP_DIR: join(dataDir, 'temp', 'manual-backups')
    }
  })

  const page = await app.firstWindow()
  page.setDefaultTimeout(DEFAULT_TIMEOUT_MS)
  await page.waitForLoadState('domcontentloaded')

  return { app, page, dataDir }
}

/**
 * Closes the app and sweeps for an orphaned sidecar `python.exe`. Normal
 * shutdown goes through `before-quit` -> `SidecarManager.stop()` ->
 * `terminateProcessTree`, which should already reap the child; a prior
 * manual E2E run left one behind once (root cause unconfirmed), so this is
 * a best-effort safety net, not a substitute for graceful shutdown. The
 * sweep only ever targets this repo's own `backend/.venv` interpreter, and
 * only instances whose parent process has already exited (i.e. actually
 * orphaned) — it never touches an unrelated/live `python.exe`.
 */
export async function closeApp(instance: LaunchedApp): Promise<void> {
  try {
    await instance.app.close()
  } catch {
    // best effort — fall through to the orphan sweep and temp-dir cleanup regardless
  }
  sweepOrphanSidecarProcesses()
  try {
    rmSync(instance.dataDir, { recursive: true, force: true })
  } catch {
    // best effort — a still-locked file here must not fail the test
  }
}

function sweepOrphanSidecarProcesses(): void {
  try {
    const escapedPath = VENV_PYTHON.replace(/'/g, "''")
    const script = [
      '$ErrorActionPreference = "SilentlyContinue"',
      `$target = '${escapedPath}'`,
      '$alive = @{}',
      'Get-Process | ForEach-Object { $alive[$_.Id] = $true }',
      'Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" |',
      '  Where-Object { $_.ExecutablePath -eq $target -and -not $alive.ContainsKey([int]$_.ParentProcessId) } |',
      '  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }'
    ].join('\n')
    execFileSync('powershell', ['-NoProfile', '-NonInteractive', '-Command', script], {
      stdio: 'ignore',
      timeout: 10_000
    })
  } catch {
    // best effort only; never fail a test because the sweep itself failed
  }
}

export interface BootstrapUser {
  username: string
  displayName: string
  password: string
}

/** The first ordinary user submitted through `/setup` (`docs/方案设计.md` §7.1: the setup form only ever creates *this* account — the fixed `admin` account is created atomically by the server alongside it, never by this form). */
export const FIRST_USER: BootstrapUser = {
  username: 'e2e_user',
  displayName: 'E2E 用户',
  password: 'TestPass123!'
}

/** Second-version bootstrap always creates the default admin under this fixed, reserved username (`BootstrapService.DEFAULT_ADMIN_USERNAME`) — it is never chosen by the setup form. */
export const FIXED_ADMIN_USERNAME = 'admin'

/** Fixed initial password the bootstrap admin account is created with (`BootstrapService.DEFAULT_ADMIN_PASSWORD`) — independent of whatever password the first ordinary user chooses. */
export const FIXED_ADMIN_INITIAL_PASSWORD = 'admin123'

/** Password the default admin sets during its mandatory first-login `/change-password` flow. */
export const ADMIN_NEW_PASSWORD = 'AdminPass456!'

/** Scopes a locator to the `.el-form-item` whose label text contains `label`, then to its input control. Only safe when at most one matching form is visible at a time — true for every screen this suite drives. */
export function formField(page: Page, label: string): ReturnType<Page['locator']> {
  return page.locator('.el-form-item', { hasText: label }).locator('input, textarea').first()
}

export async function waitForSetupOrLogin(page: Page): Promise<void> {
  await page
    .locator('h2:has-text("创建用户"), h2:has-text("登录工作手记")')
    .first()
    .waitFor({ state: 'visible' })
}

/** Submits `/setup`'s single form. The server atomically creates this account (`role=user`) plus the fixed `admin` account under its own fixed initial password (`FIXED_ADMIN_INITIAL_PASSWORD`, independent of this form's password) — this helper only drives the one form, it does not touch the admin account it implicitly creates. */
export async function bootstrapFirstUser(
  page: Page,
  user: BootstrapUser = FIRST_USER
): Promise<void> {
  await page.locator('h2:has-text("创建用户")').waitFor({ state: 'visible' })
  await formField(page, '用户名').fill(user.username)
  await formField(page, '显示名称').fill(user.displayName)
  await formField(page, '密码').fill(user.password)
  await page.locator('button:has-text("创建并继续")').click()
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
}

export async function login(page: Page, username: string, password: string): Promise<void> {
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
  await formField(page, '用户名').fill(username)
  await formField(page, '密码').fill(password)
  await page.locator('button:has-text("登录")').click()
}

/** Drives the forced `/change-password` screen a `must_change_password=true` account lands on right after login (`docs/方案设计.md` §7.2); ends back on the login screen since a successful change clears the session and requires a fresh login. */
export async function completeForcedPasswordChange(
  page: Page,
  currentPassword: string,
  newPassword: string
): Promise<void> {
  await page.locator('h2:has-text("设置新密码")').waitFor({ state: 'visible' })
  await formField(page, '当前（临时）密码').fill(currentPassword)
  await formField(page, '新密码').fill(newPassword)
  await page.locator('button:has-text("修改密码并重新登录")').click()
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
}

/**
 * Full second-version bootstrap: creates the first ordinary user + fixed
 * `admin` in one `/setup` submission, then logs into the admin account,
 * completes its mandatory first-login password change, and logs back in
 * with the new password — leaving the admin session on `/daily`.
 */
export async function bootstrapAndSignInAsAdmin(
  page: Page,
  options: { user?: BootstrapUser; newAdminPassword?: string } = {}
): Promise<void> {
  const user = options.user ?? FIRST_USER
  const newAdminPassword = options.newAdminPassword ?? ADMIN_NEW_PASSWORD
  await bootstrapFirstUser(page, user)
  await login(page, FIXED_ADMIN_USERNAME, FIXED_ADMIN_INITIAL_PASSWORD)
  await completeForcedPasswordChange(page, FIXED_ADMIN_INITIAL_PASSWORD, newAdminPassword)
  await login(page, FIXED_ADMIN_USERNAME, newAdminPassword)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
}

export async function logout(page: Page): Promise<void> {
  await page.locator('button:has-text("退出登录")').click()
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
}

export async function expectMessage(page: Page, text: string): Promise<void> {
  await expect(page.locator('.el-message', { hasText: text }).first()).toBeVisible()
}

/** Locates an `ElMessageBox` (confirm/alert) by its title text and clicks the button matching `buttonText` exactly. */
export async function confirmMessageBox(
  page: Page,
  titleText: string,
  buttonText: string
): Promise<void> {
  const box = page.locator('.el-message-box', { hasText: titleText })
  await expect(box).toBeVisible()
  await box.getByRole('button', { name: buttonText, exact: true }).click()
}

/**
 * Monkeypatches Electron's native "Save As" dialog from within the main
 * process (per `ElectronApplication.evaluate` running there) so export/
 * backup saves land at a known path instead of blocking on a real OS
 * dialog. The caller must ensure `filePath`'s parent directory already
 * exists — `ExportFileSaver`/`BackupFileSaver` only `writeFile`, they never
 * `mkdir`.
 */
export async function stubSaveDialog(app: ElectronApplication, filePath: string): Promise<void> {
  await app.evaluate(({ dialog }, targetPath) => {
    dialog.showSaveDialog = (async () => ({
      canceled: false,
      filePath: targetPath
    })) as typeof dialog.showSaveDialog
  }, filePath)
}

export function ensureDir(path: string): void {
  mkdirSync(path, { recursive: true })
}

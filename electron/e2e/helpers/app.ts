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

export interface AdminCredentials {
  username: string
  displayName: string
  password: string
}

export const DEFAULT_ADMIN: AdminCredentials = {
  username: 'admin',
  displayName: 'E2E 管理员',
  password: 'TestPass123!'
}

/** Scopes a locator to the `.el-form-item` whose label text contains `label`, then to its input control. Only safe when at most one matching form is visible at a time — true for every screen this suite drives. */
export function formField(page: Page, label: string): ReturnType<Page['locator']> {
  return page.locator('.el-form-item', { hasText: label }).locator('input, textarea').first()
}

export async function waitForSetupOrLogin(page: Page): Promise<void> {
  await page
    .locator('h2:has-text("创建管理员"), h2:has-text("登录工作手记")')
    .first()
    .waitFor({ state: 'visible' })
}

export async function bootstrapAdmin(page: Page, creds: AdminCredentials): Promise<void> {
  await page.locator('h2:has-text("创建管理员")').waitFor({ state: 'visible' })
  await formField(page, '用户名').fill(creds.username)
  await formField(page, '显示名称').fill(creds.displayName)
  await formField(page, '密码').fill(creds.password)
  await page.locator('button:has-text("创建并继续")').click()
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
}

export async function login(page: Page, username: string, password: string): Promise<void> {
  await page.locator('h2:has-text("登录工作手记")').waitFor({ state: 'visible' })
  await formField(page, '用户名').fill(username)
  await formField(page, '密码').fill(password)
  await page.locator('button:has-text("登录")').click()
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

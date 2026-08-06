import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { PROD_SIDECAR_EXECUTABLE_NAME } from './constants'

export interface SidecarLaunchPlan {
  executablePath: string
  args: string[]
  cwd: string
  /** Extra environment variables to merge into the child's env (on top of
   * `process.env`). Empty in development — the sidecar's own repo-relative
   * `.local-data/` default already matches `architecture.md` §4.3. */
  env: NodeJS.ProcessEnv
}

export type SidecarLaunchPlanResult =
  | { ok: true; plan: SidecarLaunchPlan }
  | { ok: false; reason: 'executable-not-found'; path: string }

export interface ResolveLaunchPlanOptions {
  isDev: boolean
  appPath: string
  resourcesPath: string
  /** `app.getPath('userData')`; only consumed by the production branch. */
  userDataPath: string
}

/**
 * Resolves how to launch the FastAPI sidecar for the current environment.
 *
 * Deliberately electron-free (options are always supplied by the caller,
 * never read from `electron`/`@electron-toolkit/utils` here) so this module
 * stays importable under plain Vitest: `@electron-toolkit/utils` does named
 * ESM imports from the `electron` package internally, which throws outside
 * a real Electron process. `index.ts` — the only file never loaded by
 * tests — is responsible for reading `is.dev`/`app.getAppPath()`/
 * `process.resourcesPath`/`app.getPath('userData')` and passing them in.
 *
 * Development spawns the project's own `.venv` interpreter directly (not via
 * `uv run`, whose wrapper process would leave Node holding the wrong pid on
 * Windows). Production resolves the PyInstaller onedir executable that
 * electron-builder copies to `process.resourcesPath/sidecar` (see
 * `electron-builder.yml`'s `extraResources`, produced by `PKG-01`).
 */
export function resolveSidecarLaunchPlan(
  options: ResolveLaunchPlanOptions
): SidecarLaunchPlanResult {
  return options.isDev
    ? resolveDevelopmentLaunchPlan(options.appPath)
    : resolveProductionLaunchPlan(options.resourcesPath, options.userDataPath)
}

function resolveDevelopmentLaunchPlan(appPath: string): SidecarLaunchPlanResult {
  const projectRoot = join(appPath, '..')
  const backendRoot = join(projectRoot, 'backend')
  const pythonExecutable = join(backendRoot, '.venv', 'Scripts', 'python.exe')

  if (!existsSync(pythonExecutable)) {
    return { ok: false, reason: 'executable-not-found', path: pythonExecutable }
  }

  return {
    ok: true,
    plan: {
      executablePath: pythonExecutable,
      args: ['-m', 'app'],
      cwd: backendRoot,
      env: {}
    }
  }
}

function resolveProductionLaunchPlan(
  resourcesPath: string,
  userDataPath: string
): SidecarLaunchPlanResult {
  const sidecarDir = join(resourcesPath, 'sidecar')
  const executablePath = join(sidecarDir, PROD_SIDECAR_EXECUTABLE_NAME)

  if (!existsSync(executablePath)) {
    return { ok: false, reason: 'executable-not-found', path: executablePath }
  }

  return {
    ok: true,
    plan: {
      executablePath,
      args: [],
      cwd: sidecarDir,
      env: productionDataDirEnv(userDataPath)
    }
  }
}

/**
 * The install directory must stay read-only (`architecture.md` §5), so the
 * packaged sidecar cannot fall back to `Settings`'s repo-relative
 * `.local-data/` default the way the dev interpreter does — under a
 * PyInstaller freeze that default would resolve to somewhere inside the
 * (read-only) install tree instead. These five directories match the
 * production column of `architecture.md` §4.3's runtime directory table;
 * `WEEKLY_REPORT_ENVIRONMENT=production` also disables the `/docs` route
 * (see `backend/app/main.py`).
 */
function productionDataDirEnv(userDataPath: string): NodeJS.ProcessEnv {
  return {
    WEEKLY_REPORT_ENVIRONMENT: 'production',
    WEEKLY_REPORT_DATA_DIR: join(userDataPath, 'data'),
    WEEKLY_REPORT_LOG_DIR: join(userDataPath, 'logs'),
    WEEKLY_REPORT_BACKUP_DIR: join(userDataPath, 'backups'),
    WEEKLY_REPORT_EXPORT_TEMP_DIR: join(userDataPath, 'temp', 'exports'),
    WEEKLY_REPORT_MANUAL_BACKUP_TEMP_DIR: join(userDataPath, 'temp', 'manual-backups')
  }
}

import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { PROD_SIDECAR_EXECUTABLE_NAME } from './constants'

export interface SidecarLaunchPlan {
  executablePath: string
  args: string[]
  cwd: string
}

export type SidecarLaunchPlanResult =
  | { ok: true; plan: SidecarLaunchPlan }
  | { ok: false; reason: 'executable-not-found'; path: string }

export interface ResolveLaunchPlanOptions {
  isDev: boolean
  appPath: string
  resourcesPath: string
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
 * `process.resourcesPath` and passing them in.
 *
 * Development spawns the project's own `.venv` interpreter directly (not via
 * `uv run`, whose wrapper process would leave Node holding the wrong pid on
 * Windows). Production resolves the PyInstaller onedir executable that
 * electron-builder copies to `process.resourcesPath/sidecar` (see
 * `electron-builder.yml`'s `extraResources`); until PKG-01 ships that
 * executable, this branch reports `executable-not-found` instead of
 * throwing, so callers can surface a diagnosable failed state.
 */
export function resolveSidecarLaunchPlan(
  options: ResolveLaunchPlanOptions
): SidecarLaunchPlanResult {
  return options.isDev
    ? resolveDevelopmentLaunchPlan(options.appPath)
    : resolveProductionLaunchPlan(options.resourcesPath)
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
      cwd: backendRoot
    }
  }
}

function resolveProductionLaunchPlan(resourcesPath: string): SidecarLaunchPlanResult {
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
      cwd: sidecarDir
    }
  }
}

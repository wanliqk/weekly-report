import { spawn } from 'node:child_process'

import { waitForHealthy } from './health-check'
import type { SidecarManagerDeps, SpawnSidecarProcess } from './manager'
import { resolveSidecarLaunchPlan, type ResolveLaunchPlanOptions } from './paths'
import { terminateProcessTree } from './process-kill'
import { generateRuntimeSecret } from './secret'

const spawnSidecarProcess: SpawnSidecarProcess = (command, args, options) =>
  spawn(command, args, options)

/**
 * Assembles the real `SidecarManagerDeps` used in the running app. Takes a
 * lazy `getLaunchOptions` callback (rather than `electron`/
 * `@electron-toolkit/utils` values directly) so this module itself stays
 * electron-free — only `index.ts` reads `is.dev`/`app.getAppPath()`/
 * `process.resourcesPath`, and only when the sidecar actually starts.
 */
export function createRuntimeDeps(
  getLaunchOptions: () => ResolveLaunchPlanOptions
): SidecarManagerDeps {
  return {
    resolveLaunchPlan: () => resolveSidecarLaunchPlan(getLaunchOptions()),
    spawnProcess: spawnSidecarProcess,
    waitForHealthy,
    generateSecret: generateRuntimeSecret,
    terminate: terminateProcessTree
  }
}

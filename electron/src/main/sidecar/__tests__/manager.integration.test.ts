import { execFile } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'

import { afterEach, describe, expect, it } from 'vitest'

import { createRuntimeDeps } from '../create-runtime-deps'
import { SidecarManager } from '../manager'

const execFileAsync = promisify(execFile)

// electron/src/main/sidecar/__tests__ -> electron/
const ELECTRON_APP_PATH = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', '..')

function realDevDeps(): ReturnType<typeof createRuntimeDeps> {
  return createRuntimeDeps(() => ({ isDev: true, appPath: ELECTRON_APP_PATH, resourcesPath: '' }))
}

async function isPidAlive(pid: number): Promise<boolean> {
  const { stdout } = await execFileAsync('tasklist', ['/fi', `PID eq ${pid}`, '/fo', 'csv'])
  return stdout.includes(String(pid))
}

describe('SidecarManager (real backend process)', () => {
  let manager: SidecarManager | null = null

  afterEach(async () => {
    if (manager) {
      await manager.stop('test-cleanup')
      manager = null
    }
  })

  it('spawns the real venv interpreter, gets a dynamic port, passes a real health check, and leaves no orphan on stop', async () => {
    manager = new SidecarManager(realDevDeps())

    await manager.start()

    expect(manager.getSnapshot().state).toBe('ready')

    const config = manager.getRuntimeConfig()
    expect(config).not.toBeNull()
    expect(config?.baseUrl).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/)

    const pid = manager.getChildPid()
    expect(pid).not.toBeNull()
    if (pid !== null) {
      expect(await isPidAlive(pid)).toBe(true)
    }

    await manager.stop('integration-test')
    manager = null

    if (pid !== null) {
      expect(await isPidAlive(pid)).toBe(false)
    }
  }, 20_000)

  it('assigns a different dynamic port across two consecutive launches', async () => {
    const first = new SidecarManager(realDevDeps())
    await first.start()
    const firstConfig = first.getRuntimeConfig()
    await first.stop('integration-test')

    const second = new SidecarManager(realDevDeps())
    manager = second
    await second.start()
    const secondConfig = second.getRuntimeConfig()

    expect(firstConfig).not.toBeNull()
    expect(secondConfig).not.toBeNull()
    expect(firstConfig?.baseUrl).not.toBe(secondConfig?.baseUrl)
  }, 30_000)
})

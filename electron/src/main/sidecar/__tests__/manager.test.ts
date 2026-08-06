import type { ChildProcess } from 'node:child_process'
import { EventEmitter } from 'node:events'

import { describe, expect, it, vi } from 'vitest'

import { RUNTIME_SECRET_ENV_VAR } from '../../../shared/contracts'
import { SidecarManager, type SidecarManagerDeps, type SpawnSidecarProcess } from '../manager'
import type { SidecarLaunchPlanResult } from '../paths'

class FakeChildProcess extends EventEmitter {
  stdout = new EventEmitter()
  stderr = new EventEmitter()
  pid = 1234
  exitCode: number | null = null
  signalCode: NodeJS.Signals | null = null
  kill = vi.fn()
}

function asChildProcess(child: FakeChildProcess): ChildProcess {
  return child as unknown as ChildProcess
}

function readyLine(port: number): Buffer {
  return Buffer.from(`${JSON.stringify({ event: 'sidecar_ready', port })}\n`)
}

function okPlan(env: NodeJS.ProcessEnv = {}): SidecarLaunchPlanResult {
  return {
    ok: true,
    plan: { executablePath: 'python', args: ['-m', 'app'], cwd: '/backend', env }
  }
}

function notFoundPlan(path: string): SidecarLaunchPlanResult {
  return { ok: false, reason: 'executable-not-found', path }
}

function createDeps(overrides: Partial<SidecarManagerDeps> = {}): SidecarManagerDeps {
  const spawnProcess: SpawnSidecarProcess = vi.fn(() => asChildProcess(new FakeChildProcess()))
  return {
    resolveLaunchPlan: vi.fn(okPlan),
    spawnProcess,
    waitForHealthy: vi.fn().mockResolvedValue(undefined),
    generateSecret: vi.fn(() => 'secret-value'),
    terminate: vi.fn().mockResolvedValue(undefined),
    ...overrides
  }
}

describe('SidecarManager', () => {
  it('goes straight to failed when the launch plan cannot be resolved, without spawning', async () => {
    const deps = createDeps({
      resolveLaunchPlan: vi.fn(() => notFoundPlan('/missing/python.exe'))
    })
    const manager = new SidecarManager(deps)

    await manager.start()

    const snapshot = manager.getSnapshot()
    expect(snapshot.state).toBe('failed')
    expect(snapshot.reason).toContain('/missing/python.exe')
    expect(deps.spawnProcess).not.toHaveBeenCalled()
  })

  it('transitions to ready once the sidecar announces a port and the health check passes', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({ spawnProcess: vi.fn(() => asChildProcess(child)) })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stdout.emit('data', readyLine(5001))
    await startPromise

    expect(manager.getSnapshot().state).toBe('ready')
    expect(deps.waitForHealthy).toHaveBeenCalledWith('http://127.0.0.1:5001', expect.any(Object))
    expect(manager.getRuntimeConfig()).toEqual({
      baseUrl: 'http://127.0.0.1:5001',
      runtimeSecret: 'secret-value'
    })
  })

  it('passes the runtime secret to the child via the documented env var', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({
      spawnProcess: vi.fn(() => asChildProcess(child)),
      generateSecret: vi.fn(() => 'the-secret')
    })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stdout.emit('data', readyLine(5010))
    await startPromise

    const spawnCall = (deps.spawnProcess as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      string[],
      { env: Record<string, string> }
    ]
    expect(spawnCall[2].env[RUNTIME_SECRET_ENV_VAR]).toBe('the-secret')
  })

  it('merges the launch plan env (e.g. production userData directories) into the child env', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({
      resolveLaunchPlan: vi.fn(() =>
        okPlan({
          WEEKLY_REPORT_ENVIRONMENT: 'production',
          WEEKLY_REPORT_DATA_DIR: 'C:/userData/data'
        })
      ),
      spawnProcess: vi.fn(() => asChildProcess(child))
    })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stdout.emit('data', readyLine(5011))
    await startPromise

    const spawnCall = (deps.spawnProcess as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      string[],
      { env: Record<string, string> }
    ]
    expect(spawnCall[2].env.WEEKLY_REPORT_ENVIRONMENT).toBe('production')
    expect(spawnCall[2].env.WEEKLY_REPORT_DATA_DIR).toBe('C:/userData/data')
  })

  it('fails and records the exit code when the child exits before announcing a port', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({ spawnProcess: vi.fn(() => asChildProcess(child)) })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.emit('exit', 1)
    await startPromise

    const snapshot = manager.getSnapshot()
    expect(snapshot.state).toBe('failed')
    expect(snapshot.exitCode).toBe(1)
  })

  it('fails and terminates the child when the health check times out', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({
      spawnProcess: vi.fn(() => asChildProcess(child)),
      waitForHealthy: vi.fn().mockRejectedValue(new Error('sidecar health check timed out'))
    })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stdout.emit('data', readyLine(5002))
    await startPromise

    expect(manager.getSnapshot().state).toBe('failed')
    expect(deps.terminate).toHaveBeenCalledWith(child)
  })

  it('start() does not spawn a second process while already starting or ready', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({ spawnProcess: vi.fn(() => asChildProcess(child)) })
    const manager = new SidecarManager(deps)

    const first = manager.start()
    const second = manager.start()
    child.stdout.emit('data', readyLine(5003))
    await Promise.all([first, second])

    await manager.start()

    expect(deps.spawnProcess).toHaveBeenCalledTimes(1)
  })

  it('retry() generates a fresh runtime secret and spawns a new process after a failure', async () => {
    const firstChild = new FakeChildProcess()
    const secondChild = new FakeChildProcess()
    const spawnProcess = vi
      .fn()
      .mockReturnValueOnce(asChildProcess(firstChild))
      .mockReturnValueOnce(asChildProcess(secondChild))
    const generateSecret = vi.fn().mockReturnValueOnce('secret-a').mockReturnValueOnce('secret-b')
    const waitForHealthy = vi
      .fn()
      .mockRejectedValueOnce(new Error('sidecar health check timed out'))
      .mockResolvedValueOnce(undefined)
    const deps = createDeps({ spawnProcess, generateSecret, waitForHealthy })
    const manager = new SidecarManager(deps)

    const firstStart = manager.start()
    firstChild.stdout.emit('data', readyLine(6001))
    await firstStart
    expect(manager.getSnapshot().state).toBe('failed')

    const retryPromise = manager.retry()
    secondChild.stdout.emit('data', readyLine(6002))
    await retryPromise

    expect(manager.getSnapshot().state).toBe('ready')
    expect(spawnProcess).toHaveBeenCalledTimes(2)
    const secondSpawnCall = spawnProcess.mock.calls[1] as [
      string,
      string[],
      { env: Record<string, string> }
    ]
    expect(secondSpawnCall[2].env[RUNTIME_SECRET_ENV_VAR]).toBe('secret-b')
  })

  it('retry() is a no-op unless the manager is in the failed state', async () => {
    const deps = createDeps()
    const manager = new SidecarManager(deps)

    await manager.retry()

    expect(deps.spawnProcess).not.toHaveBeenCalled()
    expect(manager.getSnapshot().state).toBe('pending')
  })

  it('stop() terminates the child and clears the runtime config', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({ spawnProcess: vi.fn(() => asChildProcess(child)) })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stdout.emit('data', readyLine(7001))
    await startPromise

    await manager.stop('test-stop')

    expect(deps.terminate).toHaveBeenCalledWith(child)
    expect(manager.getSnapshot().state).toBe('pending')
    expect(manager.getSnapshot().reason).toBe('test-stop')
    expect(manager.getRuntimeConfig()).toBeNull()
  })

  it('redacts the runtime secret from captured log lines', async () => {
    const child = new FakeChildProcess()
    const deps = createDeps({
      spawnProcess: vi.fn(() => asChildProcess(child)),
      generateSecret: vi.fn(() => 'super-secret-value')
    })
    const manager = new SidecarManager(deps)

    const startPromise = manager.start()
    child.stderr.emit('data', Buffer.from('leaked super-secret-value in traceback\n'))
    child.stdout.emit('data', readyLine(7002))
    await startPromise

    const lines = manager.getSnapshot().recentLogLines
    expect(lines.some((line) => line.includes('super-secret-value'))).toBe(false)
    expect(lines.some((line) => line.includes('***REDACTED***'))).toBe(true)
  })
})

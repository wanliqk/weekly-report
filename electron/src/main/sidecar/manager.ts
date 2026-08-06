import type { ChildProcess } from 'node:child_process'
import { EventEmitter } from 'node:events'

import {
  RUNTIME_SECRET_ENV_VAR,
  type ServiceState,
  type SidecarStatusSnapshot
} from '../../shared/contracts'
import { READY_LINE_TIMEOUT_MS } from './constants'
import type { waitForHealthy } from './health-check'
import { RedactingLogBuffer } from './log-buffer'
import type { SidecarLaunchPlanResult } from './paths'
import type { terminateProcessTree } from './process-kill'
import type { generateRuntimeSecret } from './secret'

type LifecycleState = 'idle' | 'starting' | 'ready' | 'failed' | 'stopping' | 'stopped'

function toServiceState(state: LifecycleState): ServiceState {
  switch (state) {
    case 'ready':
      return 'ready'
    case 'failed':
      return 'failed'
    default:
      return 'pending'
  }
}

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (reason: unknown) => void
}

function createDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs)
    promise.then(
      (value) => {
        clearTimeout(timer)
        resolve(value)
      },
      (error: unknown) => {
        clearTimeout(timer)
        reject(error instanceof Error ? error : new Error(String(error)))
      }
    )
  })
}

function parseAnnouncedPort(line: string): number | null {
  const trimmed = line.trim()
  if (trimmed.length === 0) {
    return null
  }
  try {
    const payload = JSON.parse(trimmed) as { event?: unknown; port?: unknown }
    if (payload.event === 'sidecar_ready' && typeof payload.port === 'number') {
      return payload.port
    }
  } catch {
    return null
  }
  return null
}

export type SpawnSidecarProcess = (
  command: string,
  args: string[],
  options: { cwd: string; env: NodeJS.ProcessEnv; stdio: ['ignore', 'pipe', 'pipe'] }
) => ChildProcess

export interface SidecarManagerDeps {
  resolveLaunchPlan: () => SidecarLaunchPlanResult
  spawnProcess: SpawnSidecarProcess
  waitForHealthy: typeof waitForHealthy
  generateSecret: typeof generateRuntimeSecret
  terminate: typeof terminateProcessTree
}

/**
 * Owns the FastAPI sidecar child process's lifecycle: launch, port capture,
 * health polling, retry, and shutdown. `start()` is idempotent so that
 * electron-vite main-process HMR reloads (which restart this whole module)
 * cannot spawn a second sidecar for a still-live instance.
 */
export class SidecarManager extends EventEmitter {
  private readonly deps: SidecarManagerDeps
  private readonly logBuffer = new RedactingLogBuffer()
  private state: LifecycleState = 'idle'
  private reason: string | null = null
  private exitCode: number | null = null
  private child: ChildProcess | null = null
  private baseUrl: string | null = null
  private runtimeSecret: string | null = null
  private startPromise: Promise<void> | null = null

  constructor(deps: SidecarManagerDeps) {
    super()
    this.deps = deps
  }

  getSnapshot(): SidecarStatusSnapshot {
    return {
      state: toServiceState(this.state),
      reason: this.reason,
      exitCode: this.exitCode,
      recentLogLines: this.logBuffer.getLines(),
      updatedAt: Date.now()
    }
  }

  getRuntimeConfig(): { baseUrl: string; runtimeSecret: string } | null {
    if (this.state !== 'ready' || this.baseUrl === null || this.runtimeSecret === null) {
      return null
    }
    return { baseUrl: this.baseUrl, runtimeSecret: this.runtimeSecret }
  }

  getChildPid(): number | null {
    return this.child?.pid ?? null
  }

  start(): Promise<void> {
    if (this.state === 'starting' || this.state === 'ready') {
      return this.startPromise ?? Promise.resolve()
    }
    this.startPromise = this.doStart()
    return this.startPromise
  }

  retry(): Promise<void> {
    if (this.state !== 'failed') {
      return this.startPromise ?? Promise.resolve()
    }
    this.setState('idle')
    return this.start()
  }

  async stop(cause: string): Promise<void> {
    if (this.state === 'idle' || this.state === 'stopped') {
      return
    }
    this.setState('stopping')
    if (this.child) {
      await this.deps.terminate(this.child)
    }
    this.child = null
    this.baseUrl = null
    this.runtimeSecret = null
    this.startPromise = null
    this.setState('stopped', cause)
  }

  private async doStart(): Promise<void> {
    this.exitCode = null
    this.logBuffer.clear()
    this.setState('starting')

    const launchPlan = this.deps.resolveLaunchPlan()
    if (!launchPlan.ok) {
      this.setState('failed', `sidecar executable not found: ${launchPlan.path}`)
      return
    }

    const runtimeSecret = this.deps.generateSecret()
    this.runtimeSecret = runtimeSecret

    const child = this.deps.spawnProcess(launchPlan.plan.executablePath, launchPlan.plan.args, {
      cwd: launchPlan.plan.cwd,
      env: {
        ...process.env,
        ...launchPlan.plan.env,
        WEEKLY_REPORT_PORT: '0',
        [RUNTIME_SECRET_ENV_VAR]: runtimeSecret
      },
      stdio: ['ignore', 'pipe', 'pipe']
    })
    this.child = child

    const portAnnounced = createDeferred<number>()
    let hasExited = false
    let stdoutBuffer = ''

    child.stdout?.on('data', (chunk: Buffer) => {
      stdoutBuffer += chunk.toString('utf8')
      let newlineIndex = stdoutBuffer.indexOf('\n')
      while (newlineIndex !== -1) {
        const line = stdoutBuffer.slice(0, newlineIndex)
        stdoutBuffer = stdoutBuffer.slice(newlineIndex + 1)
        this.logBuffer.append(line, runtimeSecret)
        const port = parseAnnouncedPort(line)
        if (port !== null) {
          portAnnounced.resolve(port)
        }
        newlineIndex = stdoutBuffer.indexOf('\n')
      }
    })

    child.stderr?.on('data', (chunk: Buffer) => {
      this.logBuffer.append(chunk.toString('utf8'), runtimeSecret)
    })

    child.once('error', (error: Error) => {
      hasExited = true
      portAnnounced.reject(error)
    })

    child.once('exit', (code: number | null) => {
      hasExited = true
      this.exitCode = code
      portAnnounced.reject(
        new Error(`sidecar exited before announcing a port (code=${String(code)})`)
      )
    })

    try {
      const port = await withTimeout(
        portAnnounced.promise,
        READY_LINE_TIMEOUT_MS,
        'timed out waiting for the sidecar to announce its port'
      )
      const baseUrl = `http://127.0.0.1:${port}`
      await this.deps.waitForHealthy(baseUrl, { isAborted: () => hasExited })
      if (hasExited) {
        throw new Error('sidecar exited during the health check')
      }
      this.baseUrl = baseUrl
      this.setState('ready')
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error)
      this.setState('failed', reason)
      if (this.child) {
        await this.deps.terminate(this.child).catch(() => {})
      }
    }
  }

  private setState(state: LifecycleState, reason: string | null = null): void {
    this.state = state
    this.reason = reason
    this.emit('state-changed', this.getSnapshot())
  }
}

let singleton: SidecarManager | null = null

/**
 * `deps` is only consulted the first time this is called (to construct the
 * singleton) — pass it every time regardless, callers after the first are
 * cheap no-ops. `index.ts` builds the real deps via `createRuntimeDeps()`
 * since it's the one file allowed to import `electron`/`@electron-toolkit/utils`.
 */
export function getSidecarManager(deps: SidecarManagerDeps): SidecarManager {
  singleton ??= new SidecarManager(deps)
  return singleton
}

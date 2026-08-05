import { execFile, type ChildProcess } from 'node:child_process'

import { GRACEFUL_SHUTDOWN_TIMEOUT_MS } from './constants'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function windowsKillTree(pid: number): Promise<void> {
  return new Promise((resolve) => {
    execFile('taskkill', ['/pid', String(pid), '/t', '/f'], () => resolve())
  })
}

export interface TerminateProcessTreeOptions {
  gracefulTimeoutMs?: number
}

/**
 * Terminates a sidecar child process and any descendants it spawned.
 *
 * On Windows, `ChildProcess.kill()` maps to a forceful `TerminateProcess`
 * on only the pid Node tracked — Windows has no real signals, and the kill
 * does not cascade to children. That matters here even though `paths.ts`
 * spawns the venv's `python.exe` directly (no `uv run` wrapper): manual
 * smoke testing showed uv-managed venvs ship a `python.exe` launcher shim
 * that re-execs into the real interpreter as a *child* process, and that
 * child in turn can spawn further children. `child.kill()` resolves the
 * tracked pid's `exit` event almost instantly, which looks like a clean
 * fast shutdown while silently orphaning the process actually running
 * uvicorn. `taskkill /t /f` walks the whole tree by pid, so on Windows we
 * use it unconditionally instead of attempting a graceful `kill()` first.
 */
export async function terminateProcessTree(
  child: ChildProcess,
  options: TerminateProcessTreeOptions = {}
): Promise<void> {
  if (child.exitCode !== null || child.signalCode !== null) {
    return
  }

  if (process.platform === 'win32') {
    if (child.pid !== undefined) {
      await windowsKillTree(child.pid)
    }
    return
  }

  const gracefulTimeoutMs = options.gracefulTimeoutMs ?? GRACEFUL_SHUTDOWN_TIMEOUT_MS

  const exited = new Promise<void>((resolve) => {
    child.once('exit', () => resolve())
  })

  child.kill()

  const timedOut = await Promise.race([
    exited.then(() => false),
    sleep(gracefulTimeoutMs).then(() => true)
  ])

  if (timedOut) {
    child.kill('SIGKILL')
    await exited
  }
}

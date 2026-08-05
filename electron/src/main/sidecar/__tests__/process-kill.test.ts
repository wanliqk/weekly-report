import type { ChildProcess } from 'node:child_process'
import { EventEmitter } from 'node:events'

import { afterEach, describe, expect, it, vi } from 'vitest'

import { terminateProcessTree } from '../process-kill'

const execFileMock = vi.fn()

vi.mock('node:child_process', () => ({
  execFile: (...args: unknown[]) => execFileMock(...args)
}))

class FakeChildProcess extends EventEmitter {
  exitCode: number | null = null
  signalCode: NodeJS.Signals | null = null
  pid = 4242
  kill = vi.fn()
}

function asChildProcess(child: FakeChildProcess): ChildProcess {
  return child as unknown as ChildProcess
}

describe('terminateProcessTree', () => {
  const originalPlatform = process.platform

  afterEach(() => {
    Object.defineProperty(process, 'platform', { value: originalPlatform })
    execFileMock.mockReset()
  })

  it('does nothing if the process has already exited', async () => {
    Object.defineProperty(process, 'platform', { value: 'win32' })
    const child = new FakeChildProcess()
    child.exitCode = 0

    await terminateProcessTree(asChildProcess(child))

    expect(execFileMock).not.toHaveBeenCalled()
    expect(child.kill).not.toHaveBeenCalled()
  })

  it('kills the whole process tree via taskkill on win32, without a graceful kill() first', async () => {
    Object.defineProperty(process, 'platform', { value: 'win32' })
    execFileMock.mockImplementation((_cmd: string, _args: string[], callback: () => void) =>
      callback()
    )
    const child = new FakeChildProcess()

    await terminateProcessTree(asChildProcess(child))

    expect(execFileMock).toHaveBeenCalledWith(
      'taskkill',
      ['/pid', '4242', '/t', '/f'],
      expect.any(Function)
    )
    expect(child.kill).not.toHaveBeenCalled()
  })

  it('kills gracefully then escalates to SIGKILL on non-Windows platforms if the process does not exit in time', async () => {
    Object.defineProperty(process, 'platform', { value: 'linux' })
    const child = new FakeChildProcess()
    child.kill = vi.fn().mockImplementation((signal?: string) => {
      if (signal === 'SIGKILL') {
        queueMicrotask(() => child.emit('exit'))
      }
    })

    await terminateProcessTree(asChildProcess(child), { gracefulTimeoutMs: 20 })

    expect(child.kill).toHaveBeenNthCalledWith(1)
    expect(child.kill).toHaveBeenNthCalledWith(2, 'SIGKILL')
    expect(execFileMock).not.toHaveBeenCalled()
  })

  it('does not escalate on non-Windows if the process exits before the graceful timeout', async () => {
    Object.defineProperty(process, 'platform', { value: 'linux' })
    const child = new FakeChildProcess()
    child.kill = vi.fn().mockImplementation(() => {
      queueMicrotask(() => child.emit('exit'))
    })

    await terminateProcessTree(asChildProcess(child), { gracefulTimeoutMs: 1000 })

    expect(child.kill).toHaveBeenCalledTimes(1)
  })
})

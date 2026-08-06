import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { PROD_SIDECAR_EXECUTABLE_NAME } from '../constants'
import { resolveSidecarLaunchPlan } from '../paths'

describe('resolveSidecarLaunchPlan', () => {
  let workDir: string

  beforeEach(() => {
    workDir = mkdtempSync(join(tmpdir(), 'sidecar-paths-'))
  })

  afterEach(() => {
    rmSync(workDir, { recursive: true, force: true })
  })

  it('resolves the venv python executable in development when it exists', () => {
    const appPath = join(workDir, 'electron')
    const pythonPath = join(workDir, 'backend', '.venv', 'Scripts', 'python.exe')
    mkdirSync(join(workDir, 'backend', '.venv', 'Scripts'), { recursive: true })
    writeFileSync(pythonPath, '')

    const result = resolveSidecarLaunchPlan({
      isDev: true,
      appPath,
      resourcesPath: '',
      userDataPath: ''
    })

    expect(result).toEqual({
      ok: true,
      plan: {
        executablePath: pythonPath,
        args: ['-m', 'app'],
        cwd: join(workDir, 'backend'),
        env: {}
      }
    })
  })

  it('reports a typed failure in development when the venv is missing', () => {
    const appPath = join(workDir, 'electron')

    const result = resolveSidecarLaunchPlan({
      isDev: true,
      appPath,
      resourcesPath: '',
      userDataPath: ''
    })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.reason).toBe('executable-not-found')
      expect(existsSync(result.path)).toBe(false)
    }
  })

  it('resolves the packaged executable in production when it exists, pointed at userData', () => {
    const executablePath = join(workDir, 'sidecar', PROD_SIDECAR_EXECUTABLE_NAME)
    mkdirSync(join(workDir, 'sidecar'), { recursive: true })
    writeFileSync(executablePath, '')
    const userDataPath = join(workDir, 'userData')

    const result = resolveSidecarLaunchPlan({
      isDev: false,
      appPath: '',
      resourcesPath: workDir,
      userDataPath
    })

    expect(result).toEqual({
      ok: true,
      plan: {
        executablePath,
        args: [],
        cwd: join(workDir, 'sidecar'),
        env: {
          WEEKLY_REPORT_ENVIRONMENT: 'production',
          WEEKLY_REPORT_DATA_DIR: join(userDataPath, 'data'),
          WEEKLY_REPORT_LOG_DIR: join(userDataPath, 'logs'),
          WEEKLY_REPORT_BACKUP_DIR: join(userDataPath, 'backups'),
          WEEKLY_REPORT_EXPORT_TEMP_DIR: join(userDataPath, 'temp', 'exports'),
          WEEKLY_REPORT_MANUAL_BACKUP_TEMP_DIR: join(userDataPath, 'temp', 'manual-backups')
        }
      }
    })
  })

  it('reports a typed failure in production when the packaged executable is missing', () => {
    const result = resolveSidecarLaunchPlan({
      isDev: false,
      appPath: '',
      resourcesPath: workDir,
      userDataPath: join(workDir, 'userData')
    })

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.reason).toBe('executable-not-found')
      expect(result.path).toBe(join(workDir, 'sidecar', PROD_SIDECAR_EXECUTABLE_NAME))
    }
  })
})

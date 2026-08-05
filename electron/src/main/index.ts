import { spawnSync } from 'node:child_process'
import { join } from 'path'

import { app, BrowserWindow, safeStorage } from 'electron'
import { electronApp, is, optimizer } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

import { registerRuntimeBridge } from './ipc/register-runtime-bridge'
import { SecureTokenStore } from './security/secure-token-store'
import { createRuntimeDeps } from './sidecar/create-runtime-deps'
import { getSidecarManager } from './sidecar/manager'
import type { ResolveLaunchPlanOptions } from './sidecar/paths'

let mainWindow: BrowserWindow | null = null
let unregisterRuntimeBridge: (() => void) | null = null

function getLaunchOptions(): ResolveLaunchPlanOptions {
  return {
    isDev: is.dev,
    appPath: app.getAppPath(),
    resourcesPath: process.resourcesPath
  }
}

const sidecarDeps = createRuntimeDeps(getLaunchOptions)

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  mainWindow.webContents.on('will-navigate', (event, targetUrl) => {
    if (targetUrl !== mainWindow?.webContents.getURL()) {
      event.preventDefault()
    }
  })

  const tokenStore = new SecureTokenStore(join(app.getPath('userData'), 'access-token.bin'), {
    isEncryptionAvailable: () => safeStorage.isEncryptionAvailable(),
    encryptString: (plainText) => safeStorage.encryptString(plainText),
    decryptString: (encrypted) => safeStorage.decryptString(encrypted)
  })
  unregisterRuntimeBridge = registerRuntimeBridge(
    getSidecarManager(sidecarDeps),
    mainWindow,
    tokenStore
  )

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    void mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  mainWindow.on('closed', () => {
    unregisterRuntimeBridge?.()
    unregisterRuntimeBridge = null
    mainWindow = null
  })
}

const hasSingleInstanceLock = app.requestSingleInstanceLock()

if (!hasSingleInstanceLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow?.isMinimized()) {
      mainWindow.restore()
    }
    mainWindow?.focus()
  })

  void app.whenReady().then(() => {
    electronApp.setAppUserModelId('com.weeklyreport.desktop')

    app.on('browser-window-created', (_, window) => {
      optimizer.watchWindowShortcuts(window)
    })

    createWindow()
    void getSidecarManager(sidecarDeps).start()

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
      }
    })
  })
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

let isQuitting = false

app.on('before-quit', (event) => {
  if (isQuitting) {
    return
  }
  isQuitting = true
  event.preventDefault()
  void getSidecarManager(sidecarDeps)
    .stop('app-quit')
    .catch(() => {})
    .finally(() => app.quit())
})

async function shutdownSidecarAndExit(cause: string, exitCode: number): Promise<void> {
  await getSidecarManager(sidecarDeps)
    .stop(cause)
    .catch(() => {})
  process.exit(exitCode)
}

process.on('SIGINT', () => {
  void shutdownSidecarAndExit('process-signal', 0)
})

process.on('SIGTERM', () => {
  void shutdownSidecarAndExit('process-signal', 0)
})

process.on('uncaughtException', (error) => {
  console.error('uncaught exception, terminating sidecar before exit', error)
  void shutdownSidecarAndExit('uncaught-exception', 1)
})

// Last-resort synchronous cleanup: `exit` handlers cannot await, so if the
// async paths above didn't run (e.g. the process is killed in a way that
// skips them) this makes a best-effort attempt to avoid a fully orphaned
// sidecar. It does not replace a Windows Job Object, which would be needed
// to guarantee cleanup when Electron itself is force-killed externally.
process.on('exit', () => {
  const pid = getSidecarManager(sidecarDeps).getChildPid()
  if (pid !== null && process.platform === 'win32') {
    try {
      spawnSync('taskkill', ['/pid', String(pid), '/t', '/f'])
    } catch {
      // best effort only
    }
  }
})

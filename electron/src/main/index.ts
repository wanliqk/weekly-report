import { spawnSync } from 'node:child_process'
import { join } from 'path'

import { app, BrowserWindow, dialog, safeStorage, session, globalShortcut } from 'electron'
import { electronApp, is, optimizer } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'

import { BackupFileSaver } from './backup/file-saver'
import { ExportFileSaver } from './export/file-saver'
import { registerRuntimeBridge } from './ipc/register-runtime-bridge'
import { registerWeComBridge } from './ipc/register-wecom-bridge'
import { SecureTokenStore, type SafeStorageAdapter } from './security/secure-token-store'
import { WeComCredentialStore } from './security/wecom-credential-store'
import { createRuntimeDeps } from './sidecar/create-runtime-deps'
import { getSidecarManager } from './sidecar/manager'
import type { ResolveLaunchPlanOptions } from './sidecar/paths'
import {
  WeComAuthWindowController,
  isAllowedWeComNavigationUrl,
  toWeComCookie
} from './wecom/auth-window-controller'
import { WeComBridgeClient } from './wecom/bridge-client'
import { WECOM_AUTH_WEB_PREFERENCES } from './wecom/constants'

let mainWindow: BrowserWindow | null = null
let unregisterRuntimeBridge: (() => void) | null = null
let unregisterWeComBridge: (() => void) | null = null

function getLaunchOptions(): ResolveLaunchPlanOptions {
  return {
    isDev: is.dev,
    appPath: app.getAppPath(),
    resourcesPath: process.resourcesPath,
    userDataPath: app.getPath('userData')
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

  const safeStorageAdapter: SafeStorageAdapter = {
    isEncryptionAvailable: () => safeStorage.isEncryptionAvailable(),
    encryptString: (plainText) => safeStorage.encryptString(plainText),
    decryptString: (encrypted) => safeStorage.decryptString(encrypted)
  }
  const tokenStore = new SecureTokenStore(
    join(app.getPath('userData'), 'access-token.bin'),
    safeStorageAdapter
  )
  const wecomCredentialStore = new WeComCredentialStore(
    join(app.getPath('userData'), 'wecom-credentials'),
    safeStorageAdapter
  )
  const wecomAuthWindowController = new WeComAuthWindowController({
    createSession: (partition) => {
      const authSession = session.fromPartition(partition)
      authSession.setPermissionRequestHandler((_contents, _permission, callback) => {
        callback(false)
      })
      authSession.on('will-download', (event) => {
        event.preventDefault()
      })
      return {
        cookies: {
          get: async (filter) => {
            const cookies = await authSession.cookies.get(filter)
            return cookies.map(toWeComCookie)
          }
        },
        clearStorageData: () => authSession.clearStorageData()
      }
    },
    createWindow: (partition) => {
      const authWindow = new BrowserWindow({
        width: 480,
        height: 720,
        show: true,
        autoHideMenuBar: true,
        parent: mainWindow ?? undefined,
        modal: true,
        webPreferences: {
          ...WECOM_AUTH_WEB_PREFERENCES,
          partition
        }
      })
      authWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
      authWindow.webContents.on('will-navigate', (event, targetUrl) => {
        if (!isAllowedWeComNavigationUrl(targetUrl)) {
          event.preventDefault()
        }
      })
      authWindow.webContents.on('will-redirect', (event, targetUrl) => {
        if (!isAllowedWeComNavigationUrl(targetUrl)) {
          event.preventDefault()
        }
      })
      return {
        loadURL: (url) => authWindow.loadURL(url),
        isDestroyed: () => authWindow.isDestroyed(),
        close: () => authWindow.close(),
        destroy: () => authWindow.destroy(),
        on: (event, listener) => {
          authWindow.on(event, listener)
        }
      }
    }
  })
  const wecomBridgeClient = new WeComBridgeClient({
    getBaseUrl: () => getSidecarManager(sidecarDeps).getRuntimeConfig()?.baseUrl ?? null,
    getMainBridgeSecret: () => getSidecarManager(sidecarDeps).getMainBridgeSecret(),
    getAccessToken: async () => (await tokenStore.getToken()).token
  })
  const exportFileSaver = new ExportFileSaver({
    showSaveDialog: async (suggestedName) => {
      if (!mainWindow) {
        return { canceled: true }
      }
      const result = await dialog.showSaveDialog(mainWindow, {
        defaultPath: suggestedName,
        filters: [{ name: 'Excel 工作簿', extensions: ['xlsx'] }]
      })
      return { canceled: result.canceled, filePath: result.filePath }
    }
  })
  const backupFileSaver = new BackupFileSaver({
    showSaveDialog: async (suggestedName) => {
      if (!mainWindow) {
        return { canceled: true }
      }
      const result = await dialog.showSaveDialog(mainWindow, {
        defaultPath: suggestedName,
        filters: [{ name: 'SQLite 数据库备份', extensions: ['db'] }]
      })
      return { canceled: result.canceled, filePath: result.filePath }
    }
  })
  unregisterRuntimeBridge = registerRuntimeBridge(
    getSidecarManager(sidecarDeps),
    mainWindow,
    tokenStore,
    exportFileSaver,
    backupFileSaver
  )
  unregisterWeComBridge = registerWeComBridge(
    mainWindow,
    wecomAuthWindowController,
    wecomCredentialStore,
    wecomBridgeClient
  )

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    void mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  mainWindow.on('closed', () => {
    unregisterRuntimeBridge?.()
    unregisterRuntimeBridge = null
    unregisterWeComBridge?.()
    unregisterWeComBridge = null
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

    globalShortcut.register('CommandOrControl+Shift+I', () => {
      mainWindow?.webContents.toggleDevTools()
    })

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

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
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

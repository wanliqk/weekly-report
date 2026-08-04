import { app, BrowserWindow } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { isAllowedNavigationUrl, getRendererDir } from './navigation-policy'
import icon from '../../resources/icon.png?asset'

// 安全基线（DESK-01）：contextIsolation=true、nodeIntegration=false、sandbox=true 不得弱化。
const WEB_PREFERENCES = {
  preload: join(__dirname, '../preload/index.js'),
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false
} as const

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 900,
    height: 670,
    show: false,
    autoHideMenuBar: true,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: WEB_PREFERENCES
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  // 占位基线：拒绝所有新窗口；外部链接打开能力属于 DESK-03，届时按域名白名单实现。
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))

  // 阻止导航到应用资源之外的任意页面；开发态仅允许受控 dev server 同源地址。
  mainWindow.webContents.on('will-navigate', (event, url) => {
    const devUrl = process.env['ELECTRON_RENDERER_URL']
    if (!isAllowedNavigationUrl(url, is.dev ? devUrl : undefined, getRendererDir(__dirname))) {
      event.preventDefault()
    }
  })

  // 开发态加载 electron-vite dev server（受控地址），生产态加载本地构建产物。
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// 导航白名单策略见 src/main/navigation-policy.ts（含 node:test 回归测试）。

function focusMainWindow(): void {
  const win = BrowserWindow.getAllWindows()[0]
  if (win) {
    if (win.isMinimized()) win.restore()
    win.focus()
  }
}

// 单实例能力（M01 最小占位）：重复启动时聚焦已有窗口并退出新实例。
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', focusMainWindow)

  app.whenReady().then(() => {
    // Set app user model id for windows
    electronApp.setAppUserModelId('com.weeklyreport.desktop')

    // Default open or close DevTools by F12 in development
    // and ignore CommandOrControl + R in production.
    // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
    app.on('browser-window-created', (_, window) => {
      optimizer.watchWindowShortcuts(window)
    })

    createWindow()

    app.on('activate', function () {
      // On macOS it's common to re-create a window in the app when the
      // dock icon is clicked and there are no other windows open.
      if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
  })

  // Quit when all windows are closed, except on macOS. There, it's common
  // for applications and their menu bar to stay active until the user quits
  // explicitly with Cmd + Q.
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })
}

import { contextBridge } from 'electron'

const desktopApi = Object.freeze({
  platform: process.platform
})

contextBridge.exposeInMainWorld('desktop', desktopApi)

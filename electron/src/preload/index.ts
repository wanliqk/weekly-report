import { contextBridge } from 'electron'

// DESK-01 最小 preload：暂不暴露任何能力。
// DESK-03 在此处按用途添加类型化白名单方法（API 基址、运行期头、Token 存取、保存对话框）。
// 禁止：通用 IPC 转发、文件系统、shell、环境变量或任意命令执行。
const api = {} as const

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // 安全基线要求 contextIsolation=true；未隔离时不暴露任何对象。
}

// DESK-03 将通过 preload contextBridge 暴露的运行期窄桥接契约（FE-01 预留）。
// 目前桌面基线（DESK-01）的 window.api 为空对象，本类型仅用于渲染进程侧的类型提示，
// 访问时必须经 client 的 getRendererBridge() 防御性读取，避免依赖具体实现。

export interface RendererBridge {
  apiBaseUrl?: string
  runtimeHeaders?: Readonly<Record<string, string>>
}

export type WindowWithBridge = Window & { api?: RendererBridge }

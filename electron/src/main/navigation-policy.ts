import { resolve, sep } from 'path'
import { fileURLToPath } from 'url'

// 导航白名单策略（纯函数，无 electron 依赖，便于 node:test 回归测试）：
// 按 URL 解析后的 origin 精确比较，禁止字符串前缀匹配（避免
// http://localhost:5173@evil.example/ 一类绕过）；生产态只放行
// rendererDir 目录内的 file: 资源。
export function isAllowedNavigationUrl(
  rawUrl: string,
  devUrl: string | undefined,
  rendererDir: string
): boolean {
  let parsed: URL
  try {
    parsed = new URL(rawUrl)
  } catch {
    return false
  }

  if (devUrl) {
    try {
      return parsed.origin === new URL(devUrl).origin
    } catch {
      return false
    }
  }

  if (parsed.protocol === 'file:') {
    try {
      return fileURLToPath(parsed).startsWith(rendererDir + sep)
    } catch {
      return false
    }
  }

  return false
}

export function getRendererDir(currentDir: string): string {
  return resolve(currentDir, '../renderer')
}

import { resolve } from 'path'
import { defineConfig } from 'electron-vite'
import type { Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

// 生产构建使用 index.html 中静态写入的严格 CSP（connect-src 'self'）。
// 开发态 HMR 需要 ws://localhost:* / http://localhost:*，仅由本插件在
// dev server 阶段注入，保证 dev 放行不会进入生产构建产物。
const DEV_CONNECT_SRC = "connect-src 'self' ws://localhost:* http://localhost:*"

function cspPlugin(): Plugin {
  return {
    name: 'weekly-report-csp',
    transformIndexHtml(html, ctx) {
      if (!ctx.server) {
        return html
      }
      return html.replace(/connect-src 'self'(?=;|")/, DEV_CONNECT_SRC)
    }
  }
}

export default defineConfig({
  main: {},
  preload: {},
  renderer: {
    resolve: {
      alias: {
        '@renderer': resolve('src/renderer/src')
      }
    },
    plugins: [vue(), cspPlugin()]
  }
})

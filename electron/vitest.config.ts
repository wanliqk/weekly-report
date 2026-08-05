import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

const rendererDir = fileURLToPath(new URL('./src/renderer/src', import.meta.url))

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@renderer': rendererDir
    }
  },
  test: {
    environment: 'node',
    include: ['src/renderer/src/**/__tests__/**/*.test.ts']
  }
})

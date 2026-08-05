import { resolve } from 'node:path'

import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: {
    alias: {
      '@renderer': resolve('src/renderer/src')
    }
  },
  test: {
    environment: 'node',
    include: ['src/renderer/src/__tests__/*.test.ts', 'src/main/**/__tests__/*.test.ts'],
    exclude: ['**/node_modules/**', '**/*.integration.test.ts']
  }
})

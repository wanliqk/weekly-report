import { defineConfig } from '@playwright/test'

/**
 * QA-09: drives the real built Electron app (main + renderer + FastAPI
 * sidecar + SQLite) through `playwright-core`'s `_electron` support — see
 * `e2e/helpers/app.ts`. This config intentionally has no `projects`/`use`
 * browser section: no test file requests the `page`/`context`/`browser`
 * fixtures from `@playwright/test`, so no Chromium/Firefox/WebKit is ever
 * launched or needs to be installed; Electron itself (already a repo
 * devDependency) is the only runtime under test.
 *
 * `npm run test:e2e` rebuilds `electron/out/**` first (see package.json) so
 * this always exercises the current source, not a stale artifact.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  outputDir: './test-results',
  reporter: [['list']]
})

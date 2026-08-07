import { expect, test } from '@playwright/test'

import {
  bootstrapFirstUser,
  closeApp,
  FIRST_USER,
  launchApp,
  login,
  type LaunchedApp
} from './helpers/app'

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('admin-guard')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('a non-admin cannot reach admin-only surfaces', async () => {
  const { page } = instance

  // The first ordinary user created by `/setup` is never an admin — the
  // fixed `admin` account is a separate account the server creates
  // alongside it (`docs/方案设计.md` §7.1).
  await bootstrapFirstUser(page)
  await login(page, FIRST_USER.username, FIRST_USER.password)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })

  // Neither admin-only nav link renders for a non-admin.
  await expect(page.locator('a:has-text("用户管理")')).toHaveCount(0)
  await expect(page.locator('a:has-text("日报管理")')).toHaveCount(0)

  // The manual-backup section on /settings is admin-only and must not render either.
  await page.locator('a:has-text("设置")').click()
  await page.locator('h1:has-text("设置")').waitFor({ state: 'visible' })
  await expect(page.locator('h2:has-text("整库手动备份")')).toHaveCount(0)

  // Direct hash navigation to either admin route must be redirected away by
  // the router guard, not merely hidden from the nav.
  await page.evaluate(() => {
    window.location.hash = '#/admin/users'
  })
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  expect(page.url()).toContain('#/daily')

  await page.evaluate(() => {
    window.location.hash = '#/admin/daily-reports'
  })
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  expect(page.url()).toContain('#/daily')
})

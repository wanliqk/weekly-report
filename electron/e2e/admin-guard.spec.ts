import { expect, test } from '@playwright/test'

import {
  bootstrapAdmin,
  closeApp,
  DEFAULT_ADMIN,
  expectMessage,
  launchApp,
  login,
  logout,
  type LaunchedApp
} from './helpers/app'

let instance: LaunchedApp

const NON_ADMIN = {
  username: 'e2e_user',
  displayName: 'E2E 普通用户',
  password: 'UserPass123!'
}

test.beforeEach(async () => {
  instance = await launchApp('admin-guard')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('a non-admin cannot reach admin-only surfaces', async () => {
  const { page } = instance

  // Bootstrap the first admin and use it to create a plain `user` account.
  await bootstrapAdmin(page, DEFAULT_ADMIN)
  await login(page, DEFAULT_ADMIN.username, DEFAULT_ADMIN.password)
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })

  await page.locator('a:has-text("用户管理")').click()
  await page.locator('button:has-text("新建用户")').click()
  const createDialog = page.locator('.el-dialog', { hasText: '新建用户' })
  await createDialog
    .locator('.el-form-item', { hasText: '用户名' })
    .locator('input')
    .fill(NON_ADMIN.username)
  await createDialog
    .locator('.el-form-item', { hasText: '显示名称' })
    .locator('input')
    .fill(NON_ADMIN.displayName)
  await createDialog
    .locator('.el-form-item', { hasText: '初始密码' })
    .locator('input')
    .fill(NON_ADMIN.password)
  await createDialog.locator('button:has-text("创建")').click()
  await expectMessage(page, '用户已创建')

  // Switch identities.
  await logout(page)
  await login(page, NON_ADMIN.username, NON_ADMIN.password)
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })

  // The nav link itself must not render for a non-admin.
  await expect(page.locator('a:has-text("用户管理")')).toHaveCount(0)

  // The backup section on /settings is admin-only and must not render either.
  await page.locator('a:has-text("个人设置")').click()
  await page.locator('h1:has-text("个人设置")').waitFor({ state: 'visible' })
  await expect(page.locator('h2:has-text("整库手动备份")')).toHaveCount(0)

  // Direct hash navigation to the admin route must be redirected away by the
  // router guard, not merely hidden from the nav.
  await page.evaluate(() => {
    window.location.hash = '#/admin/users'
  })
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })
  expect(page.url()).toContain('#/daily')
})

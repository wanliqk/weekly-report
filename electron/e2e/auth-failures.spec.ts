import { expect, test } from '@playwright/test'

import {
  bootstrapAdmin,
  closeApp,
  DEFAULT_ADMIN,
  formField,
  launchApp,
  type LaunchedApp
} from './helpers/app'

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('auth-failure')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('wrong password is rejected with a clear error and the form is not reset', async () => {
  const { page } = instance

  await bootstrapAdmin(page, DEFAULT_ADMIN)

  await formField(page, '用户名').fill(DEFAULT_ADMIN.username)
  await formField(page, '密码').fill('definitely-the-wrong-password')
  await page.locator('button:has-text("登录")').click()

  await expect(page.locator('.el-alert__title', { hasText: '用户名或密码错误' })).toBeVisible()
  // Still on the login screen — no silent redirect on failure.
  await expect(page.locator('h2:has-text("登录工作手记")')).toBeVisible()
  // The username the user typed is preserved, not wiped by the failed attempt.
  await expect(formField(page, '用户名')).toHaveValue(DEFAULT_ADMIN.username)
})

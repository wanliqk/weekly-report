import { expect, test } from '@playwright/test'

import {
  bootstrapFirstUser,
  closeApp,
  confirmMessageBox,
  DAILY_DETAIL_URL_PATTERN,
  FIRST_USER,
  formField,
  launchApp,
  login,
  type LaunchedApp
} from './helpers/app'

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('daily-validation')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('submitting with a required field blank surfaces a field-level error and keeps other input', async () => {
  const { page } = instance

  await bootstrapFirstUser(page)
  await login(page, FIRST_USER.username, FIRST_USER.password)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })

  await page.locator('button:has-text("新建日报")').click()
  await page.locator('button:has-text("创建并填写")').click()
  await page.waitForURL(DAILY_DETAIL_URL_PATTERN)

  // "今日工作内容" (required core field) is left blank on purpose; only the
  // other required core field is filled.
  await formField(page, '明日工作计划').fill('计划内容保留验证')

  await page.locator('button:has-text("提交日报")').click()
  await confirmMessageBox(page, '确认提交日报', '提交')

  // Draft save (which does not enforce required fields) succeeds first, then
  // the submit call fails server-side validation (42201) — the UI must show
  // a field-level error rather than a generic-only failure.
  await expect(page.locator('.el-message--error', { hasText: '日报内容校验失败' })).toBeVisible()
  await expect(
    page
      .locator('.el-form-item', { hasText: '今日工作内容' })
      .locator('.el-form-item__error', { hasText: '必填字段不能为空' })
  ).toBeVisible()

  // The report must still be a draft (submit did not silently succeed)...
  await expect(page.locator('.el-tag:has-text("草稿")')).toBeVisible()
  // ...and the value the user already typed into the other field survives.
  await expect(formField(page, '明日工作计划')).toHaveValue('计划内容保留验证')
})

import { expect, test } from '@playwright/test'

import {
  ADMIN_NEW_PASSWORD,
  bootstrapFirstUser,
  closeApp,
  completeForcedPasswordChange,
  DAILY_DETAIL_URL_PATTERN,
  expectMessage,
  FIRST_USER,
  FIXED_ADMIN_INITIAL_PASSWORD,
  FIXED_ADMIN_USERNAME,
  formField,
  launchApp,
  login,
  logout,
  type LaunchedApp
} from './helpers/app'

const DELETABLE_USER = {
  username: 'e2e_deletable',
  displayName: 'E2E 可删除用户',
  password: 'DeletablePass123!'
}

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('user-deletion')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('users with business records or protected roles cannot be deleted; a clean account can be', async () => {
  const { page } = instance

  // ---- give the first ordinary user a business record so it becomes non-deletable ----
  await bootstrapFirstUser(page)
  await login(page, FIRST_USER.username, FIRST_USER.password)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  await page.locator('button:has-text("新建日报")').click()
  await page.locator('button:has-text("创建并填写")').click()
  await page.waitForURL(DAILY_DETAIL_URL_PATTERN)
  await formField(page, '今日工作内容').fill('QA-10 冒烟：占用业务记录')
  await formField(page, '明日工作计划').fill('QA-10 冒烟：占用业务记录')
  await page.locator('button:has-text("保存草稿")').click()
  await expectMessage(page, '草稿已保存')
  await logout(page)

  // ---- sign in as admin (forced password change first) ----
  await login(page, FIXED_ADMIN_USERNAME, FIXED_ADMIN_INITIAL_PASSWORD)
  await completeForcedPasswordChange(page, FIXED_ADMIN_INITIAL_PASSWORD, ADMIN_NEW_PASSWORD)
  await login(page, FIXED_ADMIN_USERNAME, ADMIN_NEW_PASSWORD)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })

  // ---- admin creates a third, still-clean account ----
  await page.locator('a:has-text("用户管理")').click()
  await page.locator('h1:has-text("用户管理")').waitFor({ state: 'visible' })
  await page.locator('button:has-text("新建用户")').click()
  const createDialog = page.locator('.el-dialog', { hasText: '新建用户' })
  await createDialog
    .locator('.el-form-item', { hasText: '用户名' })
    .locator('input')
    .fill(DELETABLE_USER.username)
  await createDialog
    .locator('.el-form-item', { hasText: '显示名称' })
    .locator('input')
    .fill(DELETABLE_USER.displayName)
  await createDialog
    .locator('.el-form-item', { hasText: '初始密码' })
    .locator('input')
    .fill(DELETABLE_USER.password)
  await createDialog.locator('button:has-text("创建")').click()
  await expectMessage(page, '用户已创建')

  // ---- deletion eligibility: self and has-business-records are both blocked ----
  const adminRow = page.locator('tr', { hasText: FIXED_ADMIN_USERNAME })
  await expect(adminRow.locator('button:has-text("删除")')).toBeDisabled()
  const firstUserRow = page.locator('tr', { hasText: FIRST_USER.username })
  await expect(firstUserRow.locator('button:has-text("删除")')).toBeDisabled()
  const deletableRow = page.locator('tr', { hasText: DELETABLE_USER.username })
  await expect(deletableRow.locator('button:has-text("删除")')).toBeEnabled()

  // ---- deleting the clean account requires the exact username, then succeeds ----
  await deletableRow.locator('button:has-text("删除")').click()
  const deleteDialog = page.locator('.el-dialog', { hasText: '删除用户' })
  await expect(deleteDialog).toBeVisible()
  const confirmButton = deleteDialog.locator('button:has-text("确认删除")')

  await deleteDialog.locator('input').first().fill('wrong-username')
  await deleteDialog.locator('textarea').fill('QA-10 冒烟：验证删除流程')
  await expect(confirmButton).toBeDisabled()

  await deleteDialog.locator('input').first().fill(DELETABLE_USER.username)
  await expect(confirmButton).toBeEnabled()
  await confirmButton.click()
  await expectMessage(page, '用户已删除')

  await expect(page.locator('tr', { hasText: DELETABLE_USER.username })).toHaveCount(0)
})

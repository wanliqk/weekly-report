import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

import { expect, test } from '@playwright/test'

import {
  ADMIN_NEW_PASSWORD,
  bootstrapFirstUser,
  closeApp,
  completeForcedPasswordChange,
  confirmMessageBox,
  DAILY_DETAIL_URL_PATTERN,
  ensureDir,
  expectMessage,
  FIRST_USER,
  FIXED_ADMIN_USERNAME,
  formField,
  launchApp,
  login,
  logout,
  stubSaveDialog,
  WEEKLY_DETAIL_URL_PATTERN,
  type LaunchedApp
} from './helpers/app'

// Second-version primary path: dual-account bootstrap, forced admin password
// change, same-day multi-entry creation, admin revoke, resubmit, date-level
// archive, statistics, weekly and export. Sidecar boot + this many identity
// switches easily exceeds the config's default 120s budget on Windows.
test.setTimeout(240_000)

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('primary')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('dual bootstrap -> forced admin password change -> same-day multi-entry -> submit -> admin revoke -> resubmit -> archive -> statistics -> weekly -> export', async () => {
  const { app, page, dataDir } = instance

  // ---- 1. First-run bootstrap: one form creates the first ordinary user AND the fixed admin ----
  await bootstrapFirstUser(page)
  await expect(page.locator('.el-alert__title', { hasText: '账号创建成功' })).toBeVisible()

  // ---- 2. Default admin must change its temporary password before reaching any business page ----
  await login(page, FIXED_ADMIN_USERNAME, FIRST_USER.password)
  await page.locator('h2:has-text("设置新密码")').waitFor({ state: 'visible' })
  await expect(page.locator('.app-nav')).toHaveCount(0)

  // Route guard must bounce a manual hash navigation back, not just hide the nav link.
  await page.evaluate(() => {
    window.location.hash = '#/daily'
  })
  await page.locator('h2:has-text("设置新密码")').waitFor({ state: 'visible' })
  expect(page.url()).toContain('#/change-password')

  await completeForcedPasswordChange(page, FIRST_USER.password, ADMIN_NEW_PASSWORD)
  await expect(page.locator('.el-alert__title', { hasText: '密码已修改' })).toBeVisible()

  // ---- 3. Regular user creates two independent entries for today and submits both ----
  await login(page, FIRST_USER.username, FIRST_USER.password)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })

  async function createAndSubmitEntry(todayWork: string, tomorrowPlan: string): Promise<void> {
    await page.locator('button:has-text("新建日报")').click()
    await page.locator('button:has-text("创建并填写")').click()
    await page.waitForURL(DAILY_DETAIL_URL_PATTERN)
    await formField(page, '今日工作内容').fill(todayWork)
    await formField(page, '明日工作计划').fill(tomorrowPlan)
    await page.locator('button:has-text("提交日报")').click()
    await confirmMessageBox(page, '确认提交日报', '提交')
    await expectMessage(page, '日报已提交')
    await page.locator('button:has-text("返回我的日报")').click()
    await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  }

  await createAndSubmitEntry('QA-10 冒烟：第一篇今日工作', 'QA-10 冒烟：第一篇明日计划')
  await createAndSubmitEntry('QA-10 冒烟：第二篇今日工作', 'QA-10 冒烟：第二篇明日计划')

  await expect(page.locator('.day-entry-card')).toHaveCount(2)
  await expect(page.locator('.day-entry-card .el-tag', { hasText: '已提交' })).toHaveCount(2)

  // ---- 4. Admin revokes one of the two submissions ----
  await logout(page)
  await login(page, FIXED_ADMIN_USERNAME, ADMIN_NEW_PASSWORD)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  await page.locator('a:has-text("日报管理")').click()
  await page.locator('h1:has-text("日报管理")').waitFor({ state: 'visible' })
  await page.locator('.el-table__row').first().waitFor({ state: 'visible' })
  await expect(page.locator('.el-table__row')).toHaveCount(2)

  await page.locator('.el-table__row').first().locator('button:has-text("撤销提交")').click()
  const revokeDialog = page.locator('.el-dialog', { hasText: '撤销日报提交' })
  await expect(revokeDialog).toBeVisible()
  await revokeDialog.locator('textarea').fill('QA-10 冒烟：验证撤销流程')
  await revokeDialog.locator('button:has-text("确认撤销")').click()
  await expectMessage(page, '已撤销该条目的提交')
  await expect(page.locator('.el-table__row')).toHaveCount(1)

  // ---- 5. Regular user sees the revoked entry back as an editable draft with the admin's reason, resubmits it ----
  await logout(page)
  await login(page, FIRST_USER.username, FIRST_USER.password)
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  await expect(page.locator('.day-entry-card .el-tag', { hasText: '草稿' })).toHaveCount(1)

  await page
    .locator('.day-entry-card', { hasText: '草稿' })
    .locator('button:has-text("继续编辑")')
    .click()
  await page.waitForURL(DAILY_DETAIL_URL_PATTERN)
  await expect(
    page.locator('.el-alert', { hasText: `管理员 ${FIXED_ADMIN_USERNAME}` })
  ).toBeVisible()
  await expect(page.locator('.el-alert', { hasText: 'QA-10 冒烟：验证撤销流程' })).toBeVisible()

  await page.locator('button:has-text("提交日报")').click()
  await confirmMessageBox(page, '确认提交日报', '提交')
  await expectMessage(page, '日报已提交')
  await page.locator('button:has-text("返回我的日报")').click()
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  await expect(page.locator('.day-entry-card .el-tag', { hasText: '已提交' })).toHaveCount(2)

  // ---- 6. Date-level archive merges both entries into one official report ----
  await page.locator('button:has-text("归档当天日报")').click()
  await confirmMessageBox(page, '确认归档当天日报', '归档')
  await expectMessage(page, '当天日报已归档')
  await expect(page.locator('.detail-panel-header h2:has-text("正式日报")')).toBeVisible()
  await expect(page.locator('.day-entry-card', { hasText: '来源 1' })).toBeVisible()
  await expect(page.locator('.day-entry-card', { hasText: '来源 2' })).toBeVisible()

  // ---- 7. Statistics reflect the two archived source entries, no NaN ----
  await page.locator('a:has-text("统计")').click()
  await page.locator('h1:has-text("统计")').waitFor({ state: 'visible' })
  await expect(page.locator('text=NaN')).toHaveCount(0)
  await expect(page.locator('.feature-card', { hasText: '已写日报' })).toContainText('2 篇')

  // ---- 8. Weekly report aggregates both source entries for the day ----
  await page.locator('a:has-text("我的周报")').click()
  await page.locator('.week-range').waitFor({ state: 'visible' })
  await page.locator('button', { hasText: /生成本周周报|查看本周周报/ }).click()
  await page.waitForURL(WEEKLY_DETAIL_URL_PATTERN)
  await expect(
    page.locator('.weekly-day-card', { hasText: 'QA-10 冒烟：第一篇今日工作' })
  ).toBeVisible()
  await expect(
    page.locator('.weekly-day-card', { hasText: 'QA-10 冒烟：第二篇今日工作' })
  ).toBeVisible()
  await expect(page.locator('.weekly-day-card')).toContainText('共 2 篇来源')

  await page.locator('button:has-text("查看当天日报")').click()
  await page.locator('h1:has-text("我的日报")').waitFor({ state: 'visible' })
  await expect(page.locator('.detail-panel-header h2:has-text("正式日报")')).toBeVisible()

  // ---- 9. Export the official report and confirm a real xlsx lands on disk ----
  const downloadsDir = join(dataDir, 'downloads')
  ensureDir(downloadsDir)
  const exportPath = join(downloadsDir, 'daily-report-export.xlsx')
  await stubSaveDialog(app, exportPath)
  await page.locator('button:has-text("导出当天正式日报")').click()
  await expectMessage(page, '导出文件已保存')

  expect(existsSync(exportPath)).toBe(true)
  const exportBytes = readFileSync(exportPath)
  expect(exportBytes.length).toBeGreaterThan(0)
  // xlsx is a zip container; the first four bytes are the local file header signature "PK\x03\x04".
  expect(exportBytes.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]))
})

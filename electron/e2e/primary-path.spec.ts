import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

import { expect, test } from '@playwright/test'

import {
  bootstrapAdmin,
  closeApp,
  confirmMessageBox,
  DAILY_DETAIL_URL_PATTERN,
  DEFAULT_ADMIN,
  ensureDir,
  expectMessage,
  formField,
  launchApp,
  login,
  stubSaveDialog,
  WEEKLY_DETAIL_URL_PATTERN,
  type LaunchedApp
} from './helpers/app'

// Sidecar boot + template publish + a full daily/export/weekly chain easily
// exceeds the config's default 120s budget once Windows disk/AV overhead is
// included; this is the one test that walks the whole primary path end to
// end, so it gets its own generous ceiling.
test.setTimeout(180_000)

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('primary')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('bootstrap -> login -> template -> daily -> export -> weekly primary path', async () => {
  const { app, page, dataDir } = instance

  // ---- 1. First-run bootstrap creates the first admin + default template ----
  await bootstrapAdmin(page, DEFAULT_ADMIN)
  await expect(page.locator('.el-alert__title', { hasText: '管理员创建成功' })).toBeVisible()

  // ---- 2. Login ----
  await login(page, DEFAULT_ADMIN.username, DEFAULT_ADMIN.password)
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })

  // ---- 3. Template: add a field and publish a new immutable version ----
  await page.locator('a:has-text("模板管理")').click()
  await page.locator('h2:has-text("· v1")').waitFor({ state: 'visible' })
  await page.locator('button:has-text("新增字段")').click()
  const newFieldCard = page.locator('.field-editor').last()
  await newFieldCard.locator('.el-form-item', { hasText: '字段名称' }).locator('input').fill('备注')
  await page.locator('button:has-text("发布新版本")').click()
  await expect(page.locator('.el-message', { hasText: '已发布' })).toBeVisible()
  await page.locator('h2:has-text("· v2")').waitFor({ state: 'visible' })

  // ---- 4. Daily report: create, fill, save draft, submit, archive ----
  await page.locator('a:has-text("日报工作台")').click()
  await page.locator('button:has-text("新建日报")').click()
  await page.locator('button:has-text("创建并填写")').click()
  await page.waitForURL(DAILY_DETAIL_URL_PATTERN)
  const dailyUrl = page.url()
  const dailyReportId = dailyUrl.split('/daily/')[1]

  await formField(page, '今日工作内容').fill('完成 QA-09 E2E 主链路用例')
  await formField(page, '明日工作计划').fill('补充失败路径用例')
  await formField(page, '备注').fill('来自 Playwright')

  await page.locator('button:has-text("保存草稿")').click()
  await expectMessage(page, '草稿已保存')

  await page.locator('button:has-text("提交日报")').click()
  await confirmMessageBox(page, '确认提交日报', '提交')
  await expectMessage(page, '日报已提交')
  await page.locator('.el-tag:has-text("已提交")').waitFor({ state: 'visible' })

  await page.locator('button:has-text("归档日报")').click()
  await confirmMessageBox(page, '确认归档日报', '归档')
  await expectMessage(page, '日报已归档')
  await page.locator('.el-tag:has-text("已归档")').waitFor({ state: 'visible' })

  // ---- 5. Export: select the archived report and save a real file ----
  await page.locator('button:has-text("返回列表")').click()
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })
  await page.locator('.el-table__row').first().waitFor({ state: 'visible' })
  await page.locator('.el-table__row').first().locator('.el-checkbox__inner').click()

  const downloadsDir = join(dataDir, 'downloads')
  ensureDir(downloadsDir)
  const exportPath = join(downloadsDir, 'daily-report-export.xlsx')
  await stubSaveDialog(app, exportPath)

  await page.locator('button', { hasText: /导出所选/ }).click()
  await expectMessage(page, '导出文件已保存')

  expect(existsSync(exportPath)).toBe(true)
  const exportBytes = readFileSync(exportPath)
  expect(exportBytes.length).toBeGreaterThan(0)
  // xlsx is a zip container; the first four bytes are the local file header
  // signature "PK\x03\x04" — enough to prove a real workbook landed on disk.
  expect(exportBytes.subarray(0, 4)).toEqual(Buffer.from([0x50, 0x4b, 0x03, 0x04]))

  // ---- 6. Weekly report: generate from the archived daily report ----
  await page.locator('a:has-text("周报工作台")').click()
  await page.locator('.week-range').waitFor({ state: 'visible' })
  await page.locator('button', { hasText: /生成本周周报|查看本周周报/ }).click()
  await page.waitForURL(WEEKLY_DETAIL_URL_PATTERN)

  await expect(
    page.locator('.weekly-day-card', { hasText: '完成 QA-09 E2E 主链路用例' })
  ).toBeVisible()

  await page
    .locator('.el-form-item', { hasText: '本周补充' })
    .locator('textarea')
    .fill('本周完成了 E2E 主链路搭建')
  await page
    .locator('.el-form-item', { hasText: '下周计划' })
    .locator('textarea')
    .fill('补充更多失败路径覆盖')
  await page.locator('.el-form-item', { hasText: '问题风险' }).locator('textarea').fill('暂无')

  await page.locator('button:has-text("保存")').click()
  await expectMessage(page, '周报已保存')

  // ---- 7. Source link navigates back to the originating daily report ----
  await page.locator('button:has-text("查看来源日报")').click()
  await page.waitForURL(new RegExp(`#/daily/${dailyReportId}$`))
  await page.locator('.el-tag:has-text("已归档")').waitFor({ state: 'visible' })
})

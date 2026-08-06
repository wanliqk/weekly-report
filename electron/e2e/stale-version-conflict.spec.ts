import { expect, test } from '@playwright/test'

import {
  bootstrapAdmin,
  closeApp,
  DAILY_DETAIL_URL_PATTERN,
  DEFAULT_ADMIN,
  formField,
  launchApp,
  login,
  type LaunchedApp
} from './helpers/app'

let instance: LaunchedApp

test.beforeEach(async () => {
  instance = await launchApp('stale-version')
})

test.afterEach(async () => {
  await closeApp(instance)
})

test('a stale optimistic-lock version is rejected with a conflict, not silently overwritten', async () => {
  const { page } = instance

  await bootstrapAdmin(page, DEFAULT_ADMIN)
  await login(page, DEFAULT_ADMIN.username, DEFAULT_ADMIN.password)
  await page.locator('h1:has-text("日报工作台")').waitFor({ state: 'visible' })

  await page.locator('button:has-text("新建日报")').click()
  await page.locator('button:has-text("创建并填写")').click()
  await page.waitForURL(DAILY_DETAIL_URL_PATTERN)
  const reportId = page.url().split('/daily/')[1]

  // Simulate a concurrent edit from "another client": call the REST API
  // directly (bypassing this page's own Vue state) using the same runtime
  // config + token the renderer itself holds, to bump the report from
  // version 1 to version 2 without the open UI knowing about it.
  const bumpResult = await page.evaluate(async (id) => {
    const config = await window.runtimeBridge.api.getConfig()
    const tokenSnapshot = await window.runtimeBridge.token.get()
    if (!config || !tokenSnapshot.token) {
      throw new Error('missing runtime config or token in renderer context')
    }
    const response = await fetch(`${config.baseUrl}/api/v1/daily-reports/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${tokenSnapshot.token}`,
        [config.runtimeSecretHeader]: config.runtimeSecret
      },
      body: JSON.stringify({ version: 1, content: {} })
    })
    const body: unknown = await response.json()
    return { status: response.status, body }
  }, reportId)
  expect(bumpResult.status).toBe(200)

  // The open UI still believes it holds version 1. Editing and saving
  // through it must be rejected as a conflict, not silently overwrite the
  // version-2 state that now exists on the server.
  await formField(page, '今日工作内容').fill('本地并发编辑内容，不应覆盖服务端版本')
  await page.locator('button:has-text("保存草稿")').click()

  const conflictBox = page.locator('.el-message-box', { hasText: '版本冲突' })
  await expect(conflictBox).toBeVisible()
  await expect(conflictBox).toContainText('服务器上的日报版本已经变化')
  await conflictBox.getByRole('button', { name: '知道了', exact: true }).click()

  // No success toast for the rejected save.
  await expect(page.locator('.el-message--success', { hasText: '草稿已保存' })).toHaveCount(0)

  // Confirm on the server side that the stale save truly did not apply:
  // version is still 2 (not bumped to a third value by the rejected save)
  // and the content is still whatever the synthetic "other client" wrote,
  // not the text just typed into the stale-version form.
  const serverState = await page.evaluate(async (id) => {
    const config = await window.runtimeBridge.api.getConfig()
    const tokenSnapshot = await window.runtimeBridge.token.get()
    if (!config || !tokenSnapshot.token) {
      throw new Error('missing runtime config or token in renderer context')
    }
    const response = await fetch(`${config.baseUrl}/api/v1/daily-reports/${id}`, {
      headers: {
        Authorization: `Bearer ${tokenSnapshot.token}`,
        [config.runtimeSecretHeader]: config.runtimeSecret
      }
    })
    const body = (await response.json()) as {
      data: { version: number; content: Record<string, unknown> }
    }
    return body.data
  }, reportId)
  expect(serverState.version).toBe(2)
  expect(JSON.stringify(serverState.content)).not.toContain('本地并发编辑内容')
})

import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { isAllowedNavigationUrl } from '../src/main/navigation-policy.ts'

const devUrl = 'http://localhost:5173'
// 与主进程一致：main 的 __dirname 为 out/main，rendererDir = out/renderer
const rendererDir = resolve(import.meta.dirname, '../out/renderer')

test('dev: 允许 dev server 同源地址', () => {
  assert.equal(isAllowedNavigationUrl('http://localhost:5173/', devUrl, rendererDir), true)
  assert.equal(isAllowedNavigationUrl('http://localhost:5173/#/daily', devUrl, rendererDir), true)
})

test('dev: userinfo 注入绕过被拒绝', () => {
  assert.equal(
    isAllowedNavigationUrl('http://localhost:5173@evil.example/', devUrl, rendererDir),
    false
  )
})

test('dev: 同源欺骗域名被拒绝', () => {
  assert.equal(
    isAllowedNavigationUrl('http://localhost:5173.evil.example/', devUrl, rendererDir),
    false
  )
  assert.equal(isAllowedNavigationUrl('http://evil.example/', devUrl, rendererDir), false)
})

test('dev: 非法 URL 被拒绝', () => {
  assert.equal(isAllowedNavigationUrl('not a url', devUrl, rendererDir), false)
})

test('prod: 只放行 renderer 目录内的 file: 资源', () => {
  assert.equal(
    isAllowedNavigationUrl(
      'file:///D:/projects/weekly-report/electron/out/renderer/index.html',
      undefined,
      rendererDir
    ),
    true
  )
  assert.equal(
    isAllowedNavigationUrl(
      'file:///D:/projects/weekly-report/electron/out/renderer/assets/a.js',
      undefined,
      rendererDir
    ),
    true
  )
})

test('prod: 目录前缀绕过与目录外资源被拒绝', () => {
  assert.equal(
    isAllowedNavigationUrl(
      'file:///D:/projects/weekly-report/electron/out/renderer-evil/x.html',
      undefined,
      rendererDir
    ),
    false
  )
  assert.equal(isAllowedNavigationUrl('file:///C:/Windows/win.ini', undefined, rendererDir), false)
})

test('prod: 任意 http/https 被拒绝', () => {
  assert.equal(isAllowedNavigationUrl('http://evil.example/', undefined, rendererDir), false)
  assert.equal(isAllowedNavigationUrl('https://evil.example/', undefined, rendererDir), false)
})

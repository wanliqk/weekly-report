import { describe, expect, it } from 'vitest'
import { routes } from '../routes'

describe('FE-01 路由骨架', () => {
  it('根路由挂在默认布局下，首页为登录权限且是唯一导航项', () => {
    const layout = routes.find((record) => record.path === '/')
    expect(layout).toBeDefined()
    expect(layout?.children?.length).toBe(1)

    const home = layout?.children?.[0]
    expect(home?.path).toBe('')
    expect(home?.name).toBe('home')
    expect(home?.meta?.auth).toBe('login')
    expect(home?.meta?.title).toBe('首页')
    expect(home?.meta?.nav).toBe(true)
  })

  it('404 页面为匿名权限', () => {
    const notFound = routes.find((record) => record.path === '/404')
    expect(notFound?.name).toBe('not-found')
    expect(notFound?.meta?.auth).toBe('anonymous')
  })

  it('未匹配路径统一重定向到 404', () => {
    const fallback = routes.find((record) => record.path === '/:pathMatch(.*)*')
    expect(fallback?.redirect).toBe('/404')
  })

  it('除首页外不存在其他导航项（不预置业务假入口）', () => {
    const navItems = routes
      .flatMap((record) => record.children ?? [record])
      .filter((record) => record.meta?.nav === true)
    expect(navItems.map((record) => record.name)).toEqual(['home'])
  })
})

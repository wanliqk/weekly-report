import 'vue-router'

// 路由 meta 权限预留（FE-01）：不实现认证业务，仅声明契约。
// 取值语义：anonymous=匿名可访问；login=登录后访问；admin=仅管理员访问。
// FE-AUTH-01 将基于该信息实现导航守卫，守卫只做界面控制，不替代后端鉴权。

export type AuthLevel = 'anonymous' | 'login' | 'admin'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    auth?: AuthLevel
    nav?: boolean
  }
}

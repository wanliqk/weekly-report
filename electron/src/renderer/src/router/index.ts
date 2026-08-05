import { createRouter, createWebHashHistory } from 'vue-router'
import { routes } from './routes'

// 生产态 renderer 通过 file:// 加载本地构建产物，使用 hash 历史模式，
// 无需服务端路由配置；HMR 与生产行为一致。
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 导航守卫仅做界面控制（文档标题），权限守卫由 FE-AUTH-01 基于 meta.auth 补充。
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - Weekly Report` : 'Weekly Report'
})

export default router

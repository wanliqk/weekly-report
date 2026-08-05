import type { RouteRecordRaw } from 'vue-router'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import HomeView from '../views/HomeView.vue'
import NotFoundView from '../views/NotFoundView.vue'

// 路由骨架（FE-01）：meta.auth 预留 anonymous/login/admin 权限信息，
// 导航守卫在 FE-AUTH-01 实现；meta.nav 为 true 时出现在侧边导航。
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: HomeView,
        meta: { title: '首页', auth: 'login', nav: true }
      }
    ]
  },
  {
    path: '/404',
    name: 'not-found',
    component: NotFoundView,
    meta: { title: '页面不存在', auth: 'anonymous' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'catch-all',
    redirect: '/404'
  }
]

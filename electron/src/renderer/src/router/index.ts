import { createRouter, createWebHashHistory } from 'vue-router'

import AppLayout from '@renderer/layouts/AppLayout.vue'
import { useAuthStore } from '@renderer/stores/auth'
import { useSidecarStore } from '@renderer/stores/sidecar'
import DailyCreateView from '@renderer/views/DailyCreateView.vue'
import DailyDetailView from '@renderer/views/DailyDetailView.vue'
import DailyListView from '@renderer/views/DailyListView.vue'
import HomeView from '@renderer/views/HomeView.vue'
import LoginView from '@renderer/views/LoginView.vue'
import SetupView from '@renderer/views/SetupView.vue'
import TemplatesView from '@renderer/views/TemplatesView.vue'
import UsersView from '@renderer/views/UsersView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    guestOnly?: boolean
    setupOnly?: boolean
  }
}

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'entry', component: HomeView },
    { path: '/setup', name: 'setup', component: SetupView, meta: { setupOnly: true } },
    { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: 'daily', name: 'daily', component: DailyListView },
        { path: 'daily/new', name: 'daily-create', component: DailyCreateView },
        { path: 'daily/:id', name: 'daily-detail', component: DailyDetailView },
        { path: 'templates', name: 'templates', component: TemplatesView },
        {
          path: 'admin/users',
          name: 'users',
          component: UsersView,
          meta: { requiresAdmin: true }
        }
      ]
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach(async (to) => {
  const sidecarStore = useSidecarStore()
  if (sidecarStore.serviceState !== 'ready') {
    return to.path === '/' ? true : { path: '/' }
  }
  const authStore = useAuthStore()
  await authStore.initialize()
  if (authStore.systemInitialized === false) {
    return to.meta.setupOnly ? true : { path: '/setup' }
  }
  if (to.path === '/') {
    return { path: authStore.isAuthenticated ? '/daily' : '/login' }
  }
  if (to.meta.setupOnly) {
    return { path: authStore.isAuthenticated ? '/daily' : '/login' }
  }
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { path: '/daily' }
  }
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login' }
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { path: '/daily' }
  }
  return true
})

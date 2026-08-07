import { createRouter, createWebHashHistory } from 'vue-router'

import AppLayout from '@renderer/layouts/AppLayout.vue'
import { useAuthStore } from '@renderer/stores/auth'
import { useSidecarStore } from '@renderer/stores/sidecar'
import AdminDailyReportsView from '@renderer/views/AdminDailyReportsView.vue'
import ChangePasswordView from '@renderer/views/ChangePasswordView.vue'
import DailyCreateView from '@renderer/views/DailyCreateView.vue'
import DailyDetailView from '@renderer/views/DailyDetailView.vue'
import DailyListView from '@renderer/views/DailyListView.vue'
import HomeView from '@renderer/views/HomeView.vue'
import LoginView from '@renderer/views/LoginView.vue'
import SettingsView from '@renderer/views/SettingsView.vue'
import SetupView from '@renderer/views/SetupView.vue'
import StatisticsView from '@renderer/views/StatisticsView.vue'
import TemplatesView from '@renderer/views/TemplatesView.vue'
import UsersView from '@renderer/views/UsersView.vue'
import WeeklyDetailView from '@renderer/views/WeeklyDetailView.vue'
import WeeklyListView from '@renderer/views/WeeklyListView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    guestOnly?: boolean
    setupOnly?: boolean
    forcedPasswordChangeOnly?: boolean
  }
}

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'entry', component: HomeView },
    { path: '/setup', name: 'setup', component: SetupView, meta: { setupOnly: true } },
    { path: '/login', name: 'login', component: LoginView, meta: { guestOnly: true } },
    {
      path: '/change-password',
      name: 'change-password',
      component: ChangePasswordView,
      meta: { requiresAuth: true, forcedPasswordChangeOnly: true }
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: 'daily', name: 'daily', component: DailyListView },
        { path: 'daily/new', name: 'daily-create', component: DailyCreateView },
        { path: 'daily/:id', name: 'daily-detail', component: DailyDetailView },
        { path: 'weekly', name: 'weekly', component: WeeklyListView },
        { path: 'weekly/:id', name: 'weekly-detail', component: WeeklyDetailView },
        { path: 'statistics', name: 'statistics', component: StatisticsView },
        { path: 'templates', name: 'templates', component: TemplatesView },
        { path: 'settings', name: 'settings', component: SettingsView },
        {
          path: 'admin/daily-reports',
          name: 'admin-daily-reports',
          component: AdminDailyReportsView,
          meta: { requiresAdmin: true }
        },
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
    return { path: entryPathFor(authStore) }
  }
  if (to.meta.setupOnly) {
    return { path: authStore.isAuthenticated ? entryPathFor(authStore) : '/login' }
  }
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return { path: entryPathFor(authStore) }
  }
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login' }
  }
  if (to.meta.forcedPasswordChangeOnly && !authStore.mustChangePassword) {
    return { path: '/daily' }
  }
  if (to.meta.requiresAuth && !to.meta.forcedPasswordChangeOnly && authStore.mustChangePassword) {
    return { path: '/change-password' }
  }
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { path: '/daily' }
  }
  return true
})

function entryPathFor(authStore: ReturnType<typeof useAuthStore>): string {
  if (!authStore.isAuthenticated) {
    return '/login'
  }
  return authStore.mustChangePassword ? '/change-password' : '/daily'
}

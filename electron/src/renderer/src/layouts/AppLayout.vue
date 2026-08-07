<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

async function signOut(): Promise<void> {
  await authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand-block">
        <span class="brand-mark">周</span>
        <div>
          <strong>工作手记</strong>
          <small>WEEKLY REPORT</small>
        </div>
      </div>
      <nav class="app-nav" aria-label="主导航">
        <RouterLink to="/daily">我的日报</RouterLink>
        <RouterLink to="/weekly">我的周报</RouterLink>
        <RouterLink to="/statistics">统计</RouterLink>
        <RouterLink to="/templates">模板管理</RouterLink>
        <RouterLink to="/settings">设置</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin/daily-reports">日报管理</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin/users">用户管理</RouterLink>
      </nav>
      <div class="account-card">
        <span>{{ authStore.currentUser?.display_name }}</span>
        <small
          >@{{ authStore.currentUser?.username }} ·
          {{ authStore.isAdmin ? '管理员' : '用户' }}</small
        >
        <div class="account-actions">
          <el-button link @click="router.push('/settings')">设置</el-button>
          <el-button link @click="signOut">退出登录</el-button>
        </div>
      </div>
    </aside>
    <section class="app-content">
      <RouterView />
    </section>
  </div>
</template>

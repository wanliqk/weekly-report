<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import { resetApiClient } from '@renderer/api/client'
import { useAuthStore } from '@renderer/stores/auth'
import { useSidecarStore } from '@renderer/stores/sidecar'
import StartupView from '@renderer/views/StartupView.vue'

const sidecarStore = useSidecarStore()
const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const authReady = ref(false)
let resolving = false

async function resolveEntryRoute(): Promise<void> {
  if (resolving || sidecarStore.serviceState !== 'ready') return
  resolving = true
  authReady.value = false
  resetApiClient()
  try {
    await authStore.initialize()
    if (authStore.systemInitialized === false) {
      await router.replace('/setup')
    } else if (!authStore.isAuthenticated) {
      if (route.path !== '/login') await router.replace('/login')
    } else if (authStore.mustChangePassword) {
      if (route.path !== '/change-password') await router.replace('/change-password')
    } else if (
      route.path === '/' ||
      route.path === '/login' ||
      route.path === '/setup' ||
      route.path === '/change-password'
    ) {
      await router.replace('/daily')
    } else if (route.meta.requiresAdmin && !authStore.isAdmin) {
      await router.replace('/daily')
    }
  } finally {
    authReady.value = true
    resolving = false
  }
}

watch(
  () => sidecarStore.serviceState,
  (state) => {
    if (state === 'ready') void resolveEntryRoute()
    else authReady.value = false
  }
)

onMounted(async () => {
  await sidecarStore.init()
  await resolveEntryRoute()
})
</script>

<template>
  <StartupView v-if="sidecarStore.serviceState !== 'ready'" />
  <main v-else-if="!authReady" class="auth-loading">正在恢复安全登录状态…</main>
  <RouterView v-else />
</template>

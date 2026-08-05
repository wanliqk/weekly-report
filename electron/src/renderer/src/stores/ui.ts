import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

// 全局 UI 状态（FE-01）：跨页面共享的加载计数，用于全局加载指示。
// api 层拦截器在请求开始/结束时增减计数；页面级 loading 仍由页面自行管理。
export const useUiStore = defineStore('ui', () => {
  const pendingRequests = ref(0)
  const isLoading = computed(() => pendingRequests.value > 0)

  function beginRequest(): void {
    pendingRequests.value += 1
  }

  function endRequest(): void {
    pendingRequests.value = Math.max(0, pendingRequests.value - 1)
  }

  return { pendingRequests, isLoading, beginRequest, endRequest }
})

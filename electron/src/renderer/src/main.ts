import './assets/main.css'
import 'element-plus/dist/index.css'

import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { configureApiAuth } from './api/client'
import App from './App.vue'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const application = createApp(App).use(pinia)
const authStore = useAuthStore(pinia)

configureApiAuth({
  getAccessToken: () => authStore.accessToken,
  onTokenInvalid: async () => {
    await authStore.handleTokenInvalid()
    if (router.currentRoute.value.path !== '/login') {
      await router.replace('/login')
    }
  },
  onPasswordChangeRequired: async () => {
    if (router.currentRoute.value.path !== '/change-password') {
      await router.replace('/change-password')
    }
  }
})

application.use(router).use(ElementPlus, { locale: zhCn }).mount('#app')

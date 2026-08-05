<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const form = reactive({ username: '', password: '' })

async function submit(): Promise<void> {
  errorMessage.value = null
  submitting.value = true
  try {
    await authStore.login(form.username, form.password)
    await router.replace('/daily')
  } catch (error) {
    errorMessage.value = userMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page login-page">
    <section class="auth-intro">
      <span class="eyebrow">PRIVATE DESKTOP</span>
      <h1>把每天的进展，沉淀成清晰的周度脉络。</h1>
      <p>日报、模板、周报与导出都由本机服务统一处理，不经过外部云端。</p>
    </section>
    <section class="auth-card">
      <div class="auth-card-heading">
        <span>欢迎回来</span>
        <h2>登录工作手记</h2>
      </div>
      <el-alert
        v-if="route.query.initialized === '1'"
        title="管理员创建成功，请登录"
        type="success"
        show-icon
        :closable="false"
      />
      <el-alert
        v-if="!authStore.secureStorageAvailable"
        title="系统安全存储不可用，已禁止登录以避免明文保存 Token"
        type="error"
        show-icon
        :closable="false"
      />
      <el-alert
        v-else-if="authStore.initializationError"
        :title="authStore.initializationError"
        type="warning"
        show-icon
        :closable="false"
      />
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        :closable="false"
      />
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-button
          class="auth-submit"
          type="primary"
          native-type="submit"
          :loading="submitting"
          :disabled="!authStore.secureStorageAvailable || !form.username || !form.password"
        >
          登录
        </el-button>
      </el-form>
    </section>
  </main>
</template>

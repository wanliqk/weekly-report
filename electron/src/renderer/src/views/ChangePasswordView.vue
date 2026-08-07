<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const form = reactive({ currentPassword: '', newPassword: '' })

async function submit(): Promise<void> {
  errorMessage.value = null
  submitting.value = true
  try {
    await authStore.changePassword(form.currentPassword, form.newPassword)
    await router.replace({ path: '/login', query: { passwordChanged: '1' } })
  } catch (error) {
    errorMessage.value = userMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro">
      <span class="eyebrow">SECURITY</span>
      <h1>先修改临时密码，再继续使用。</h1>
      <p>
        {{
          authStore.currentUser?.display_name
        }}，你当前使用的是临时密码。为了账号安全，必须先设置一个新密码才能继续访问日报、周报和其他业务功能。
      </p>
      <ul>
        <li>新密码至少 8 位</li>
        <li>修改成功后需要用新密码重新登录</li>
      </ul>
    </section>
    <section class="auth-card">
      <div class="auth-card-heading">
        <span>强制修改密码</span>
        <h2>设置新密码</h2>
      </div>
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        :closable="false"
      />
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="当前（临时）密码">
          <el-input
            v-model="form.currentPassword"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="form.newPassword"
            type="password"
            show-password
            maxlength="128"
            autocomplete="new-password"
          />
          <span class="field-hint">至少 8 位，修改后所有旧 Token 立即失效。</span>
        </el-form-item>
        <el-button
          class="auth-submit"
          type="primary"
          native-type="submit"
          :loading="submitting"
          :disabled="!form.currentPassword || form.newPassword.length < 8"
        >
          修改密码并重新登录
        </el-button>
      </el-form>
    </section>
  </main>
</template>

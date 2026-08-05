<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const form = reactive({ username: 'admin', displayName: '', password: '' })

async function submit(): Promise<void> {
  errorMessage.value = null
  submitting.value = true
  try {
    await authStore.bootstrap({
      username: form.username,
      display_name: form.displayName,
      password: form.password
    })
    await router.replace({ path: '/login', query: { initialized: '1' } })
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
      <span class="eyebrow">FIRST RUN</span>
      <h1>建立你的本地工作空间</h1>
      <p>创建首位管理员后，系统会同时生成个人设置和默认日报模板。全部数据只保存在这台电脑。</p>
      <ul>
        <li>默认包含“今日工作内容”和“明日工作计划”</li>
        <li>密码仅以 Argon2id 哈希保存</li>
        <li>初始化完成后不可重复创建首位管理员</li>
      </ul>
    </section>
    <section class="auth-card">
      <div class="auth-card-heading">
        <span>步骤 1 / 1</span>
        <h2>创建管理员</h2>
      </div>
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        :closable="false"
      />
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" maxlength="64" autocomplete="username" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.displayName" maxlength="100" placeholder="例如：张三" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            maxlength="128"
            autocomplete="new-password"
          />
          <span class="field-hint">至少 8 位。</span>
        </el-form-item>
        <el-button
          class="auth-submit"
          type="primary"
          native-type="submit"
          :loading="submitting"
          :disabled="!form.username || !form.displayName || form.password.length < 8"
        >
          创建并继续
        </el-button>
      </el-form>
    </section>
  </main>
</template>

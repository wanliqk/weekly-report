<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordForm = reactive({ currentPassword: '', newPassword: '' })

async function submitPasswordChange(): Promise<void> {
  passwordSubmitting.value = true
  try {
    await authStore.changePassword(passwordForm.currentPassword, passwordForm.newPassword)
    ElMessage.success('密码已修改，请重新登录')
    passwordDialogVisible.value = false
    await router.replace('/login')
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    passwordSubmitting.value = false
  }
}

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
        <RouterLink to="/daily">日报工作台</RouterLink>
        <RouterLink to="/templates">模板管理</RouterLink>
        <RouterLink v-if="authStore.isAdmin" to="/admin/users">用户管理</RouterLink>
      </nav>
      <div class="account-card">
        <span>{{ authStore.currentUser?.display_name }}</span>
        <small
          >@{{ authStore.currentUser?.username }} ·
          {{ authStore.isAdmin ? '管理员' : '用户' }}</small
        >
        <div class="account-actions">
          <el-button link @click="passwordDialogVisible = true">修改密码</el-button>
          <el-button link @click="signOut">退出登录</el-button>
        </div>
      </div>
    </aside>
    <section class="app-content">
      <RouterView />
    </section>
  </div>

  <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px">
    <el-form label-position="top" @submit.prevent="submitPasswordChange">
      <el-form-item label="当前密码">
        <el-input v-model="passwordForm.currentPassword" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="passwordForm.newPassword" type="password" show-password />
        <span class="field-hint">至少 8 位，修改后所有旧 Token 立即失效。</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="passwordSubmitting" @click="submitPasswordChange">
        确认修改
      </el-button>
    </template>
  </el-dialog>
</template>

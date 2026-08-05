<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { createUser, listUsers, resetUserPassword, updateUser } from '@renderer/api/users'
import { useAuthStore } from '@renderer/stores/auth'
import type { UserData, UserRole } from '@renderer/types/user'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const users = ref<UserData[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const createDialogVisible = ref(false)
const createForm = reactive({
  username: '',
  displayName: '',
  password: '',
  role: 'user' as UserRole
})

const editDialogVisible = ref(false)
const editOriginal = ref<UserData | null>(null)
const editForm = reactive({
  id: '',
  displayName: '',
  role: 'user' as UserRole,
  isActive: true
})

const resetDialogVisible = ref(false)
const resetTarget = ref<UserData | null>(null)
const resetPassword = ref('')

async function loadUsers(nextPage = page.value): Promise<void> {
  loading.value = true
  try {
    const result = await listUsers(nextPage, pageSize)
    users.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  Object.assign(createForm, { username: '', displayName: '', password: '', role: 'user' })
  createDialogVisible.value = true
}

async function submitCreate(): Promise<void> {
  submitting.value = true
  try {
    await createUser({
      username: createForm.username,
      password: createForm.password,
      display_name: createForm.displayName,
      role: createForm.role
    })
    ElMessage.success('用户已创建，并已生成默认设置与日报模板')
    createDialogVisible.value = false
    await loadUsers(1)
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    submitting.value = false
  }
}

function openEdit(user: UserData): void {
  editOriginal.value = user
  Object.assign(editForm, {
    id: user.id,
    displayName: user.display_name,
    role: user.role,
    isActive: user.is_active
  })
  editDialogVisible.value = true
}

async function submitEdit(): Promise<void> {
  const original = editOriginal.value
  if (!original) return
  const payload: { display_name?: string; role?: UserRole; is_active?: boolean } = {}
  if (editForm.displayName !== original.display_name) payload.display_name = editForm.displayName
  if (editForm.role !== original.role) payload.role = editForm.role
  if (editForm.isActive !== original.is_active) payload.is_active = editForm.isActive
  if (Object.keys(payload).length === 0) {
    editDialogVisible.value = false
    return
  }
  if (payload.role || payload.is_active !== undefined) {
    try {
      await ElMessageBox.confirm(
        '角色或启用状态变化会立即使该用户现有 Token 失效，是否继续？',
        '确认账号变更',
        { type: 'warning', confirmButtonText: '继续修改', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }

  submitting.value = true
  try {
    const updated = await updateUser(editForm.id, payload)
    ElMessage.success('用户信息已更新')
    editDialogVisible.value = false
    if (updated.id === authStore.currentUser?.id) {
      if (payload.role || payload.is_active !== undefined) {
        await authStore.handleTokenInvalid()
        await router.replace('/login')
        return
      }
      authStore.currentUser = updated
    }
    await loadUsers()
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    submitting.value = false
  }
}

function openReset(user: UserData): void {
  resetTarget.value = user
  resetPassword.value = ''
  resetDialogVisible.value = true
}

async function submitReset(): Promise<void> {
  const target = resetTarget.value
  if (!target) return
  submitting.value = true
  try {
    await resetUserPassword(target.id, resetPassword.value)
    ElMessage.success('密码已重置，该用户所有旧 Token 已失效')
    resetDialogVisible.value = false
    if (target.id === authStore.currentUser?.id) {
      await authStore.handleTokenInvalid()
      await router.replace('/login')
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    submitting.value = false
  }
}

function formatCreatedAt(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">ADMINISTRATION</span>
        <h1>用户管理</h1>
        <p>仅管理账号元数据、角色和登录凭据；管理员无法从这里查看他人的日报或周报正文。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </header>

    <section class="table-card">
      <el-table v-loading="loading" :data="users" row-key="id">
        <el-table-column label="用户" min-width="220">
          <template #default="scope">
            <div class="user-cell">
              <span class="user-avatar">{{ scope.row.display_name.slice(0, 1) }}</span>
              <div>
                <strong>{{ scope.row.display_name }}</strong>
                <small>@{{ scope.row.username }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? 'warning' : 'info'">
              {{ scope.row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope">
            <span :class="scope.row.is_active ? 'status-dot-label' : 'status-dot-label disabled'">
              {{ scope.row.is_active ? '已启用' : '已禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="scope">{{ formatCreatedAt(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="openEdit(scope.row)">编辑</el-button>
            <el-button link @click="openReset(scope.row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        class="table-pagination"
        layout="prev, pager, next, total"
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        @current-change="loadUsers"
      />
    </section>
  </main>

  <el-dialog v-model="createDialogVisible" title="新建用户" width="480px">
    <el-form label-position="top">
      <el-form-item label="用户名"
        ><el-input v-model="createForm.username" maxlength="64"
      /></el-form-item>
      <el-form-item label="显示名称"
        ><el-input v-model="createForm.displayName" maxlength="100"
      /></el-form-item>
      <el-form-item label="初始密码">
        <el-input v-model="createForm.password" type="password" show-password maxlength="128" />
        <span class="field-hint">至少 8 位。</span>
      </el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="createForm.role">
          <el-radio value="user">普通用户</el-radio>
          <el-radio value="admin">管理员</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="
          !createForm.username || !createForm.displayName || createForm.password.length < 8
        "
        @click="submitCreate"
        >创建</el-button
      >
    </template>
  </el-dialog>

  <el-dialog v-model="editDialogVisible" title="编辑用户" width="480px">
    <el-form label-position="top">
      <el-form-item label="显示名称"
        ><el-input v-model="editForm.displayName" maxlength="100"
      /></el-form-item>
      <el-form-item label="角色">
        <el-radio-group v-model="editForm.role">
          <el-radio value="user">普通用户</el-radio>
          <el-radio value="admin">管理员</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="账号状态">
        <el-switch v-model="editForm.isActive" active-text="启用" inactive-text="禁用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resetDialogVisible" title="重置密码" width="440px">
    <p class="dialog-copy">
      为 {{ resetTarget?.display_name }} 设置新密码。保存后，该账号所有旧 Token 立即失效。
    </p>
    <el-form label-position="top">
      <el-form-item label="新密码">
        <el-input v-model="resetPassword" type="password" show-password maxlength="128" />
        <span class="field-hint">至少 8 位。</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="resetDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="resetPassword.length < 8"
        @click="submitReset"
        >确认重置</el-button
      >
    </template>
  </el-dialog>
</template>

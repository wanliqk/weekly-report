<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'

import { userMessage } from '@renderer/api/client'
import { getCapabilities, getMySettings, updateMySettings } from '@renderer/api/settings'
import { createManualBackup, downloadManualBackupFile } from '@renderer/api/system'
import { useAuthStore } from '@renderer/stores/auth'
import type { CapabilitiesData, SettingsData } from '@renderer/types/settings'

const authStore = useAuthStore()
const loading = ref(true)
const settings = ref<SettingsData | null>(null)
const capabilities = ref<CapabilitiesData | null>(null)
const savingArchiveSetting = ref(false)
const creatingBackup = ref(false)

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [settingsData, capabilitiesData] = await Promise.all([getMySettings(), getCapabilities()])
    settings.value = settingsData
    capabilities.value = capabilitiesData
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

async function toggleAutoArchive(enabled: boolean): Promise<void> {
  if (!settings.value) {
    return
  }
  const previous = settings.value.auto_archive_on_submit
  settings.value.auto_archive_on_submit = enabled
  savingArchiveSetting.value = true
  try {
    settings.value = await updateMySettings(enabled)
  } catch (error) {
    settings.value.auto_archive_on_submit = previous
    ElMessage.error(userMessage(error))
  } finally {
    savingArchiveSetting.value = false
  }
}

function showWecomPlaceholder(): void {
  ElMessage.info('企业微信同步功能暂未开放')
}

async function createAndSaveBackup(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '整库备份会导出全部用户的账号、日报和周报数据，不只是你自己的内容，请仅在确有需要时创建并妥善保管导出的文件。备份文件 15 分钟内未下载将自动失效。',
      '创建整库备份',
      {
        confirmButtonText: '仍要创建并保存',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
  } catch {
    return
  }
  creatingBackup.value = true
  try {
    const created = await createManualBackup()
    const file = await downloadManualBackupFile(created.id)
    const outcome = await window.runtimeBridge.backupFile.save(
      file.fileName,
      new Uint8Array(file.data)
    )
    if (outcome.status === 'saved') {
      ElMessage.success('备份文件已保存')
    } else if (outcome.status === 'canceled') {
      ElMessage.info('已取消保存')
    } else {
      ElMessage.error('保存备份文件失败，请检查目标位置后重试')
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    creatingBackup.value = false
  }
}
</script>

<template>
  <main class="workspace-page workspace-page-narrow">
    <header class="page-heading">
      <div>
        <span class="eyebrow">SETTINGS</span>
        <h1>个人设置</h1>
        <p>管理归档方式与同步能力；管理员可在本页创建整库备份。</p>
      </div>
    </header>

    <section v-loading="loading" class="settings-sections">
      <div class="editor-card">
        <div class="section-heading">
          <div>
            <span>ARCHIVE</span>
            <h2>提交后自动归档</h2>
          </div>
          <el-switch
            :model-value="settings?.auto_archive_on_submit ?? false"
            :loading="savingArchiveSetting"
            :disabled="!settings"
            @change="(value) => toggleAutoArchive(Boolean(value))"
          />
        </div>
        <p class="field-hint">开启后，提交日报会在同一操作中直接归档，无需再手动归档一次。</p>
        <p class="field-hint">当前时区固定为 {{ settings?.timezone ?? 'Asia/Shanghai' }}。</p>
      </div>

      <div class="editor-card">
        <div class="section-heading">
          <div>
            <span>WECOM</span>
            <h2>企业微信同步</h2>
          </div>
          <el-tag type="info" effect="plain">功能暂未开放</el-tag>
        </div>
        <p class="field-hint">
          企业微信同步入口仅作占位展示，当前版本不会连接企业微信或发起任何相关网络请求。
        </p>
        <el-button :disabled="!capabilities" @click="showWecomPlaceholder">连接企业微信</el-button>
      </div>

      <div v-if="authStore.isAdmin" class="editor-card">
        <div class="section-heading">
          <div>
            <span>ADMIN</span>
            <h2>整库手动备份</h2>
          </div>
        </div>
        <el-alert type="warning" :closable="false" show-icon>
          <template #title>
            备份文件包含全体用户的账号、日报和周报数据，不仅是你自己的内容，下载后请妥善保管
          </template>
        </el-alert>
        <p class="field-hint">创建后生成一次性下载文件，15 分钟内未下载会自动失效。</p>
        <el-button type="primary" :loading="creatingBackup" @click="createAndSaveBackup">
          创建备份并保存到本机
        </el-button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import { createDailyReport } from '@renderer/api/daily-reports'
import { todayInShanghai } from '@renderer/utils/daily-form'

const router = useRouter()
const workDate = ref(todayInShanghai())
const submitting = ref(false)

async function create(): Promise<void> {
  if (!workDate.value) {
    ElMessage.error('请选择工作日期')
    return
  }
  submitting.value = true
  try {
    const report = await createDailyReport(workDate.value)
    await router.replace(`/daily/${report.id}`)
  } catch (error) {
    const existingId = existingReportId(error)
    if (existingId) {
      ElMessage.info('该日期已有日报，已为你打开')
      await router.replace(`/daily/${existingId}`)
      return
    }
    ElMessage.error(userMessage(error))
  } finally {
    submitting.value = false
  }
}

function existingReportId(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.code !== 40901) {
    return null
  }
  if (
    typeof error.data === 'object' &&
    error.data !== null &&
    'existing_report_id' in error.data &&
    typeof error.data.existing_report_id === 'string'
  ) {
    return error.data.existing_report_id
  }
  return null
}
</script>

<template>
  <main class="workspace-page workspace-page-narrow">
    <header class="page-heading">
      <div>
        <span class="eyebrow">NEW DAILY REPORT</span>
        <h1>新建日报</h1>
        <p>日期以 Asia/Shanghai 为准。允许补写历史日报，也允许提前创建未来计划。</p>
      </div>
    </header>

    <section class="create-card">
      <div class="create-card-copy">
        <span>工作日期</span>
        <h2>这份日报记录哪一天？</h2>
        <p>每个账号同一天只能创建一份日报；创建时会锁定当前模板版本。</p>
      </div>
      <el-date-picker
        v-model="workDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        placeholder="选择工作日期"
      />
      <div class="create-card-actions">
        <el-button @click="router.push('/daily')">返回</el-button>
        <el-button type="primary" :loading="submitting" @click="create">创建并填写</el-button>
      </div>
    </section>
  </main>
</template>

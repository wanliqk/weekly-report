<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import { createDailyReport } from '@renderer/api/daily-reports'
import { generateClientRequestId, todayInShanghai } from '@renderer/utils/daily-form'

const route = useRoute()
const router = useRouter()
const workDate = ref(
  typeof route.query.work_date === 'string' ? route.query.work_date : todayInShanghai()
)
const submitting = ref(false)

async function create(): Promise<void> {
  if (!workDate.value) {
    ElMessage.error('请选择工作日期')
    return
  }
  submitting.value = true
  try {
    const report = await createDailyReport(workDate.value, generateClientRequestId())
    await router.replace(`/daily/${report.id}`)
  } catch (error) {
    if (error instanceof ApiError && error.code === 40905) {
      ElMessage.error('该日期已归档，无法新增日报')
      await router.replace({ path: '/daily', query: { date: workDate.value } })
      return
    }
    ElMessage.error(userMessage(error))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="workspace-page workspace-page-narrow">
    <header class="page-heading">
      <div>
        <span class="eyebrow">NEW DAILY REPORT</span>
        <h1>新建日报</h1>
        <p>
          日期以 Asia/Shanghai
          为准。日期未归档时可以创建多篇独立日报；可补写历史日报，也可提前创建未来计划。
        </p>
      </div>
    </header>

    <section class="create-card">
      <div class="create-card-copy">
        <span>工作日期</span>
        <h2>这份日报记录哪一天？</h2>
        <p>同一天可以创建多篇日报，提交后由你在“我的日报”中手动发起当天归档。</p>
      </div>
      <el-date-picker
        v-model="workDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        placeholder="选择工作日期"
      />
      <div class="create-card-actions">
        <el-button @click="router.push({ path: '/daily', query: { date: workDate } })">
          返回
        </el-button>
        <el-button type="primary" :loading="submitting" @click="create">创建并填写</el-button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import {
  createDailyReport,
  deleteDailyReport,
  getDailyReport,
  saveDailyReport,
  submitDailyReport
} from '@renderer/api/daily-reports'
import DynamicFieldInput from '@renderer/components/DynamicFieldInput.vue'
import type { DailyContent, DailyFieldValue, DailyReportData } from '@renderer/types/daily-report'
import {
  dailyFieldErrors,
  dailyStatusLabel,
  formatShanghaiTime,
  generateClientRequestId,
  initializeDailyContent,
  todayInShanghai
} from '@renderer/utils/daily-form'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const actionRunning = ref(false)
const report = ref<DailyReportData | null>(null)
const content = ref<DailyContent>({})
const fieldErrors = ref<Record<string, string>>({})

const reportId = computed(() => String(route.params.id))
const isCreating = computed(() => reportId.value === 'new')
const workDateFromQuery = computed(() =>
  typeof route.query.work_date === 'string' ? route.query.work_date : todayInShanghai()
)
const editable = computed(() => report.value?.status === 'draft')
const visibleFields = computed(() =>
  [...(report.value?.template_snapshot ?? [])]
    .filter((field) => field.enabled)
    .sort((left, right) => left.sort_order - right.sort_order)
)

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    if (isCreating.value) {
      const created = await createDailyReport(workDateFromQuery.value, generateClientRequestId())
      assignReport(created)
      await router.replace(`/daily/${created.id}`)
      return
    }
    const loadedReport = await getDailyReport(reportId.value)
    assignReport(loadedReport)
  } catch (error) {
    if (isCreating.value && error instanceof ApiError && error.code === 40905) {
      ElMessage.error('该日期已归档，无法新增日报')
      await router.replace({ path: '/daily', query: { date: workDateFromQuery.value } })
      return
    }
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

function assignReport(nextReport: DailyReportData): void {
  report.value = nextReport
  content.value = initializeDailyContent(nextReport.template_snapshot, nextReport.content)
  fieldErrors.value = {}
}

function backToCalendar(): void {
  router.push({ path: '/daily', query: { date: report.value?.work_date } })
}

function updateField(fieldKey: string, value: DailyFieldValue): void {
  content.value[fieldKey] = value
  delete fieldErrors.value[fieldKey]
}

async function save(showSuccess = true): Promise<boolean> {
  if (!report.value || report.value.status !== 'draft') {
    return false
  }
  saving.value = true
  fieldErrors.value = {}
  try {
    const saved = await saveDailyReport(report.value.id, report.value.version, content.value)
    assignReport(saved)
    if (showSuccess) {
      ElMessage.success('草稿已保存')
    }
    return true
  } catch (error) {
    handleOperationError(error)
    return false
  } finally {
    saving.value = false
  }
}

async function submit(): Promise<void> {
  if (!report.value || report.value.status !== 'draft') {
    return
  }
  try {
    await ElMessageBox.confirm(
      '提交后正文不可继续编辑；需要在“我的日报”中手动发起当天归档才会生成正式日报。',
      '确认提交日报',
      { confirmButtonText: '提交', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  if (!(await save(false)) || !report.value) {
    return
  }
  actionRunning.value = true
  try {
    const submitted = await submitDailyReport(report.value.id, report.value.version)
    assignReport(submitted)
    ElMessage.success('日报已提交')
  } catch (error) {
    handleOperationError(error)
  } finally {
    actionRunning.value = false
  }
}

async function removeDraft(): Promise<void> {
  if (!report.value || report.value.status !== 'draft') {
    return
  }
  try {
    await ElMessageBox.confirm('确认删除这份草稿吗？此操作不可撤销。', '删除草稿', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    })
  } catch {
    return
  }
  actionRunning.value = true
  try {
    await deleteDailyReport(report.value.id, report.value.version)
    ElMessage.success('草稿已删除')
    backToCalendar()
  } catch (error) {
    handleOperationError(error)
  } finally {
    actionRunning.value = false
  }
}

function handleOperationError(error: unknown): void {
  fieldErrors.value = dailyFieldErrors(error)
  if (error instanceof ApiError && error.code === 40904) {
    void ElMessageBox.alert(
      '服务器上的日报版本已经变化。当前输入仍保留，请复制需要的内容后重新打开日报。',
      '版本冲突',
      { confirmButtonText: '知道了', type: 'warning' }
    )
    return
  }
  if (error instanceof ApiError && error.code === 40905) {
    void ElMessageBox.alert('这一天已经被归档，这份草稿已不再可操作。', '日期已归档', {
      confirmButtonText: '返回我的日报',
      type: 'warning'
    }).then(() => backToCalendar())
    return
  }
  ElMessage.error(userMessage(error))
}
</script>

<template>
  <main class="workspace-page workspace-page-form">
    <header class="page-heading">
      <div>
        <span class="eyebrow">DAILY REPORT</span>
        <h1>{{ report?.work_date ?? '日报详情' }}</h1>
        <p v-if="report">
          模板快照 {{ report.template_version_id }} · 内容版本 v{{ report.version }}
        </p>
      </div>
      <div v-if="report" class="page-actions">
        <el-tag
          :type="
            report.status === 'draft'
              ? 'warning'
              : report.status === 'submitted'
                ? 'success'
                : 'info'
          "
          effect="plain"
          size="large"
        >
          {{ dailyStatusLabel(report.status) }}
        </el-tag>
        <el-button @click="backToCalendar">返回我的日报</el-button>
      </div>
    </header>

    <section v-loading="loading" class="report-editor-card">
      <template v-if="report">
        <el-alert
          v-if="report.status !== 'draft'"
          :title="
            report.status === 'archived'
              ? '这份日报已经归档，只能查看。'
              : '这份日报已经提交，只能查看，等待当天归档或管理员撤销。'
          "
          type="info"
          :closable="false"
          show-icon
        />
        <el-alert
          v-if="report.last_revocation"
          type="warning"
          :closable="false"
          show-icon
          :title="`管理员 ${report.last_revocation.actor_username} 于 ${formatShanghaiTime(report.last_revocation.revoked_at)} 撤销了此前的提交：${report.last_revocation.reason}`"
        />

        <el-form class="dynamic-report-form" label-position="top">
          <DynamicFieldInput
            v-for="field in visibleFields"
            :key="field.field_key"
            :field="field"
            :model-value="content[field.field_key] ?? null"
            :disabled="!editable"
            :error="fieldErrors[field.field_key]"
            @update:model-value="updateField(field.field_key, $event)"
          />
        </el-form>

        <div class="report-metadata">
          <span>最后更新：{{ formatShanghaiTime(report.updated_at) }}</span>
          <span>提交时间：{{ formatShanghaiTime(report.submitted_at) }}</span>
          <span>归档时间：{{ formatShanghaiTime(report.archived_at) }}</span>
        </div>

        <footer class="report-actions">
          <div class="report-primary-actions">
            <el-button
              v-if="editable"
              type="danger"
              plain
              :loading="actionRunning"
              @click="removeDraft"
            >
              删除草稿
            </el-button>
            <el-button v-if="editable" :loading="saving" @click="save()">保存草稿</el-button>
            <el-button
              v-if="editable"
              type="primary"
              :loading="actionRunning"
              :disabled="saving"
              @click="submit"
            >
              提交日报
            </el-button>
          </div>
        </footer>
      </template>
    </section>
  </main>
</template>

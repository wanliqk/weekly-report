<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import { getCapabilities } from '@renderer/api/settings'
import { archiveDay } from '@renderer/api/daily-report-days'
import {
  createDailyReport,
  deleteDailyReport,
  getDailyReport,
  saveDailyReport,
  submitDailyReport
} from '@renderer/api/daily-reports'
import { createDailyReportExport, downloadDailyReportExportFile } from '@renderer/api/exports'
import DynamicFieldInput from '@renderer/components/DynamicFieldInput.vue'
import WeComSyncDialog from '@renderer/components/wecom/WeComSyncDialog.vue'
import { useAuthStore } from '@renderer/stores/auth'
import type { DailyContent, DailyFieldValue, DailyReportData } from '@renderer/types/daily-report'
import {
  dailyFieldErrors,
  dailyStatusLabel,
  formatShanghaiTime,
  generateClientRequestId,
  initializeDailyContent,
  sanitizeDailyContent,
  todayInShanghai
} from '@renderer/utils/daily-form'
import { invalidExportDayIds } from '@renderer/utils/export'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const loading = ref(true)
const saving = ref(false)
const actionRunning = ref(false)
const exporting = ref(false)
const wecomEnabled = ref(false)
const wecomDialogVisible = ref(false)
const report = ref<DailyReportData | null>(null)
const content = ref<DailyContent>({})
const fieldErrors = ref<Record<string, string>>({})

const reportId = computed(() => String(route.params.id))
const isCreating = computed(() => reportId.value === 'new')
const workDateFromQuery = computed(() =>
  typeof route.query.work_date === 'string' ? route.query.work_date : todayInShanghai()
)
const editable = computed(() => report.value?.status === 'draft')
const currentUserDisplayName = computed(() => authStore.currentUser?.display_name ?? '')
const visibleFields = computed(() =>
  [...(report.value?.template_snapshot ?? [])]
    .filter((field) => field.enabled)
    .sort((left, right) => left.sort_order - right.sort_order)
)

onMounted(() => {
  void load()
  void loadCapabilities()
})

async function loadCapabilities(): Promise<void> {
  try {
    wecomEnabled.value = (await getCapabilities()).wecom_sync
  } catch {
    wecomEnabled.value = false
  }
}

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
  content.value = initializeDailyContent(
    nextReport.template_snapshot,
    nextReport.content,
    currentUserDisplayName.value
  )
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
    const saved = await saveDailyReport(
      report.value.id,
      report.value.version,
      sanitizeDailyContent(visibleFields.value, content.value, currentUserDisplayName.value)
    )
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
      '提交后正文不可继续编辑，系统会自动归档当天日报；若当天还有其他草稿未提交，将无法自动归档，需要处理后手动归档。',
      '确认提交并归档',
      { confirmButtonText: '提交并归档', cancelButtonText: '取消', type: 'warning' }
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
    await archiveAfterSubmit(submitted.work_date)
  } catch (error) {
    handleOperationError(error)
  } finally {
    actionRunning.value = false
  }
}

async function archiveAfterSubmit(workDate: string): Promise<void> {
  if (!report.value) {
    return
  }
  try {
    await archiveDay(workDate)
    const refreshed = await getDailyReport(report.value.id)
    assignReport(refreshed)
    ElMessage.success('日报已提交并归档')
  } catch (error) {
    if (error instanceof ApiError && error.code === 40906) {
      ElMessage.warning('日报已提交，但当天还有其他草稿未提交，无法自动归档，请处理后手动归档')
      return
    }
    ElMessage.warning('日报已提交，但自动归档失败，请稍后在“我的日报”中手动归档')
  }
}

async function exportReport(): Promise<void> {
  if (!report.value) {
    return
  }
  exporting.value = true
  try {
    const job = await createDailyReportExport({ daily_report_day_ids: [report.value.day_id] })
    if (job.status === 'failed') {
      ElMessage.error('导出生成失败，请稍后重试')
      return
    }
    if (job.record_count === 0) {
      ElMessage.warning('所选或筛选范围内没有可导出的正式日报')
      return
    }
    const file = await downloadDailyReportExportFile(job.id)
    const outcome = await window.runtimeBridge.exportFile.save(
      file.fileName,
      new Uint8Array(file.data)
    )
    if (outcome.status === 'saved') {
      ElMessage.success('导出文件已保存')
    } else if (outcome.status === 'canceled') {
      ElMessage.info('已取消保存')
    } else {
      ElMessage.error('保存导出文件失败，请检查目标位置后重试')
    }
  } catch (error) {
    if (invalidExportDayIds(error)) {
      ElMessage.error('所选日期不可导出（需为本人已归档日期）')
    } else {
      ElMessage.error(userMessage(error))
    }
  } finally {
    exporting.value = false
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
        <el-button v-if="report.status === 'archived'" :loading="exporting" @click="exportReport">
          导出日报
        </el-button>
        <el-button
          v-if="report.status === 'archived' && wecomEnabled"
          type="primary"
          @click="wecomDialogVisible = true"
        >
          同步到企业微信
        </el-button>
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
            :default-owner="currentUserDisplayName"
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
              提交并归档
            </el-button>
          </div>
        </footer>
      </template>
    </section>

    <WeComSyncDialog
      v-if="report && report.status === 'archived' && wecomEnabled"
      v-model="wecomDialogVisible"
      :daily-report-day-id="report.day_id"
      :work-date="report.work_date"
    />
  </main>
</template>

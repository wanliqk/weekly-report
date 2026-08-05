<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import {
  getWeeklyReport,
  regenerateWeeklyReport,
  saveWeeklyReport
} from '@renderer/api/weekly-reports'
import type { WeeklyReportData } from '@renderer/types/weekly-report'
import { formatShanghaiTime } from '@renderer/utils/daily-form'
import { formatWeeklyFieldValue } from '@renderer/utils/weekly-report'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const regenerating = ref(false)
const report = ref<WeeklyReportData | null>(null)
const editableText = reactive({ supplement: '', next_week_plan: '', risks: '' })

const reportId = computed(() => String(route.params.id))

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    assignReport(await getWeeklyReport(reportId.value))
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

function assignReport(nextReport: WeeklyReportData): void {
  report.value = nextReport
  editableText.supplement = nextReport.content.supplement
  editableText.next_week_plan = nextReport.content.next_week_plan
  editableText.risks = nextReport.content.risks
}

async function save(): Promise<void> {
  if (!report.value) {
    return
  }
  saving.value = true
  try {
    const saved = await saveWeeklyReport(report.value.id, report.value.version, {
      supplement: editableText.supplement,
      next_week_plan: editableText.next_week_plan,
      risks: editableText.risks
    })
    assignReport(saved)
    ElMessage.success('周报已保存')
  } catch (error) {
    handleOperationError(error)
  } finally {
    saving.value = false
  }
}

async function regenerate(): Promise<void> {
  if (!report.value) {
    return
  }
  try {
    await ElMessageBox.confirm(
      '重新生成会用当前已归档日报重新计算本周内容，并且会覆盖你已经保存的“本周补充/下周计划/问题风险”，此操作不可撤销。',
      '确认重新生成周报',
      {
        confirmButtonText: '仍要覆盖重新生成',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
  } catch {
    return
  }
  regenerating.value = true
  try {
    const regenerated = await regenerateWeeklyReport(report.value.id, report.value.version)
    assignReport(regenerated)
    ElMessage.success('周报已重新生成')
  } catch (error) {
    handleOperationError(error)
  } finally {
    regenerating.value = false
  }
}

function handleOperationError(error: unknown): void {
  if (error instanceof ApiError && error.code === 40904) {
    void ElMessageBox.alert(
      '服务器上的周报版本已经变化。当前输入仍保留，请复制需要的内容后重新打开周报。',
      '版本冲突',
      { confirmButtonText: '知道了', type: 'warning' }
    )
    return
  }
  ElMessage.error(userMessage(error))
}
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">WEEKLY REPORT</span>
        <h1 v-if="report">{{ report.week_start }} 至 {{ report.week_end }}</h1>
        <h1 v-else>周报详情</h1>
        <p v-if="report">
          生成时间 {{ formatShanghaiTime(report.generated_at) }} · 内容版本 v{{ report.version }}
        </p>
      </div>
      <div class="page-actions">
        <el-button @click="router.push('/weekly')">返回列表</el-button>
      </div>
    </header>

    <section v-loading="loading" class="report-editor-card">
      <template v-if="report">
        <el-empty
          v-if="report.content.days.length === 0"
          description="这一周没有已归档日报，来源部分为空"
        />
        <div v-else class="weekly-days">
          <article v-for="day in report.content.days" :key="day.work_date" class="weekly-day-card">
            <header>
              <strong>{{ day.work_date }}</strong>
              <el-button link type="primary" @click="router.push(`/daily/${day.daily_report_id}`)">
                查看来源日报
              </el-button>
            </header>
            <dl>
              <template v-for="field in day.fields" :key="field.field_key">
                <dt>{{ field.label }}</dt>
                <dd>{{ formatWeeklyFieldValue(field.value) }}</dd>
              </template>
            </dl>
          </article>
        </div>

        <el-form class="weekly-edit-form" label-position="top">
          <el-form-item label="本周补充">
            <el-input v-model="editableText.supplement" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="下周计划">
            <el-input v-model="editableText.next_week_plan" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="问题风险">
            <el-input v-model="editableText.risks" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>

        <footer class="report-actions">
          <div class="report-primary-actions">
            <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            <el-button :loading="regenerating" @click="regenerate">重新生成</el-button>
          </div>
        </footer>
      </template>
    </section>
  </main>
</template>

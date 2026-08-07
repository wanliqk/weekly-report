<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import { archiveDay, getDayDetail } from '@renderer/api/daily-report-days'
import { deleteDailyReport } from '@renderer/api/daily-reports'
import { createDailyReportExport, downloadDailyReportExportFile } from '@renderer/api/exports'
import type { DailyReportListItemData } from '@renderer/types/daily-report'
import type {
  DailyReportDayDetailData,
  DayArchiveSnapshotEntryData
} from '@renderer/types/daily-report-day'
import type { ExportCreateRequest } from '@renderer/types/export'
import type { TemplateFieldData } from '@renderer/types/template'
import {
  dailyStatusLabel,
  formatDailyFieldValue,
  formatShanghaiTime
} from '@renderer/utils/daily-form'
import {
  dayCellStatus,
  dayCellStatusLabel,
  dayCellStatusTagType
} from '@renderer/utils/daily-report-day'
import { invalidExportDayIds } from '@renderer/utils/export'

const route = useRoute()
const router = useRouter()

const workDate = computed(() => String(route.params.date))
const detail = ref<DailyReportDayDetailData | null>(null)
const detailLoading = ref(false)
const archiving = ref(false)
const exporting = ref(false)

const cellStatus = computed(() => dayCellStatus(detail.value ?? undefined))

async function loadDetail(): Promise<void> {
  detailLoading.value = true
  try {
    detail.value = await getDayDetail(workDate.value)
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => void loadDetail())
watch(workDate, () => void loadDetail())

function visibleSnapshotFields(entry: DayArchiveSnapshotEntryData): TemplateFieldData[] {
  return [...entry.template_snapshot]
    .filter((field) => field.enabled)
    .sort((left, right) => left.sort_order - right.sort_order)
}

function backToCalendar(): void {
  router.push({ path: '/daily', query: { date: workDate.value } })
}

function createEntry(): void {
  router.push({ path: '/daily/new', query: { work_date: workDate.value } })
}

async function removeDraft(entry: DailyReportListItemData): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${workDate.value} 的这份草稿吗？此操作不可撤销。`,
      '删除草稿',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
  } catch {
    return
  }
  try {
    await deleteDailyReport(entry.id, entry.version)
    ElMessage.success('草稿已删除')
    await loadDetail()
  } catch (error) {
    handleActionError(error)
  }
}

async function confirmArchive(): Promise<void> {
  if (!detail.value) {
    return
  }
  try {
    await ElMessageBox.confirm(
      `${workDate.value} 共有 ${detail.value.submitted_count} 篇已提交条目将合并为一份正式日报。归档后不可再新增或撤销。`,
      '确认归档当天日报',
      {
        confirmButtonText: '归档',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
  } catch {
    return
  }
  archiving.value = true
  try {
    await archiveDay(workDate.value)
    ElMessage.success('当天日报已归档')
    await loadDetail()
  } catch (error) {
    handleActionError(error)
  } finally {
    archiving.value = false
  }
}

function handleActionError(error: unknown): void {
  if (error instanceof ApiError && [40904, 40905, 40906, 40907].includes(error.code)) {
    ElMessage.warning(userMessage(error))
    void loadDetail()
    return
  }
  ElMessage.error(userMessage(error))
}

async function exportSelectedDay(): Promise<void> {
  const dayId = detail.value?.entries[0]?.day_id
  if (!dayId) {
    return
  }
  await runExport({ daily_report_day_ids: [dayId] })
}

async function runExport(request: ExportCreateRequest): Promise<void> {
  exporting.value = true
  try {
    const job = await createDailyReportExport(request)
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
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">{{ workDate }}</span>
        <h1>{{ cellStatus === 'archived' ? '正式日报' : '当日日报' }}</h1>
        <p>查看并管理这一天的日报条目；提交后可发起归档，归档后自动汇总为一份正式日报。</p>
      </div>
      <div class="page-actions">
        <el-tag :type="dayCellStatusTagType(cellStatus)" effect="plain" size="large">
          {{ dayCellStatusLabel(cellStatus) }}
        </el-tag>
        <el-button @click="backToCalendar">返回日历</el-button>
      </div>
    </header>

    <section class="day-detail-card">
      <div v-loading="detailLoading" class="detail-panel-body">
        <template v-if="detail">
          <template v-if="detail.status === 'archived'">
            <el-empty
              v-if="!detail.archive_snapshot || detail.archive_snapshot.entries.length === 0"
              description="正式日报为空"
            />
            <article
              v-for="(entry, index) in detail.archive_snapshot?.entries ?? []"
              :key="entry.daily_report_id"
              class="day-entry-card"
            >
              <header>
                <strong>来源 {{ index + 1 }} · {{ formatShanghaiTime(entry.submitted_at) }}</strong>
                <el-button
                  link
                  type="primary"
                  @click="router.push(`/daily/${entry.daily_report_id}`)"
                >
                  查看来源条目
                </el-button>
              </header>
              <dl>
                <template v-for="field in visibleSnapshotFields(entry)" :key="field.field_key">
                  <dt>{{ field.label }}</dt>
                  <dd>{{ formatDailyFieldValue(entry.content[field.field_key] ?? null) }}</dd>
                </template>
              </dl>
            </article>
            <p class="field-hint">
              归档时间：{{ formatShanghaiTime(detail.archived_at) }} · 共
              {{ detail.archived_count }} 篇来源
            </p>
            <div class="day-panel-actions">
              <el-button :loading="exporting" @click="exportSelectedDay">
                导出当天正式日报
              </el-button>
            </div>
          </template>

          <template v-else>
            <el-empty
              v-if="detail.entries.length === 0"
              description="这一天还没有日报，点击下方按钮新建一篇"
            />
            <article v-for="entry in detail.entries" :key="entry.id" class="day-entry-card">
              <header>
                <el-tag
                  :type="entry.status === 'draft' ? 'warning' : 'success'"
                  effect="plain"
                  size="small"
                >
                  {{ dailyStatusLabel(entry.status) }}
                </el-tag>
                <span class="field-hint"
                  >v{{ entry.version }} · {{ formatShanghaiTime(entry.updated_at) }}</span
                >
              </header>
              <div class="day-entry-actions">
                <el-button link type="primary" @click="router.push(`/daily/${entry.id}`)">
                  {{ entry.status === 'draft' ? '继续编辑' : '查看' }}
                </el-button>
                <el-button
                  v-if="entry.status === 'draft'"
                  link
                  type="danger"
                  @click="removeDraft(entry)"
                >
                  删除草稿
                </el-button>
              </div>
            </article>

            <div class="day-panel-actions">
              <el-button type="primary" @click="createEntry">新建日报</el-button>
              <el-tooltip
                v-if="!detail.can_archive"
                :content="detail.archive_disabled_reason ?? ''"
                placement="top"
              >
                <span><el-button disabled>归档当天日报</el-button></span>
              </el-tooltip>
              <el-button v-else type="warning" :loading="archiving" @click="confirmArchive">
                归档当天日报
              </el-button>
            </div>
          </template>
        </template>
      </div>
    </section>
  </main>
</template>

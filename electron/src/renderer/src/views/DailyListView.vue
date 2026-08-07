<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { getDayDetail, getMonthSummary } from '@renderer/api/daily-report-days'
import { createDailyReportExport, downloadDailyReportExportFile } from '@renderer/api/exports'
import type {
  DailyDayCellStatus,
  DailyReportDayMonthItemData
} from '@renderer/types/daily-report-day'
import type { ExportCreateRequest } from '@renderer/types/export'
import { todayInShanghai } from '@renderer/utils/daily-form'
import {
  dayCellStatus,
  dayCellStatusLabel,
  dayCellStatusTagType
} from '@renderer/utils/daily-report-day'
import { invalidExportDayIds } from '@renderer/utils/export'

const route = useRoute()
const router = useRouter()

const initialDate = typeof route.query.date === 'string' ? route.query.date : todayInShanghai()
const calendarDate = ref(parseCalendarDate(initialDate))

const monthItems = ref<DailyReportDayMonthItemData[]>([])
const monthLoading = ref(false)
const exporting = ref(false)
const resolvingDate = ref(false)

const month = computed(() => formatCalendarDate(calendarDate.value).slice(0, 7))
const selectedDate = computed(() => formatCalendarDate(calendarDate.value))
const itemsByDate = computed(() => new Map(monthItems.value.map((item) => [item.work_date, item])))

const legendStatuses: DailyDayCellStatus[] = ['none', 'draft', 'submitted', 'mixed', 'archived']

function formatCalendarDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseCalendarDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function shiftMonth(delta: number): void {
  calendarDate.value = new Date(
    calendarDate.value.getFullYear(),
    calendarDate.value.getMonth() + delta,
    1
  )
}

function goToday(): void {
  calendarDate.value = parseCalendarDate(todayInShanghai())
}

async function selectDate(day: string): Promise<void> {
  if (resolvingDate.value) {
    return
  }
  resolvingDate.value = true
  try {
    const dayDetail = await getDayDetail(day)
    if (dayDetail.status === 'archived') {
      router.push({ name: 'daily-day', params: { date: day } })
      return
    }
    if (dayDetail.entries.length === 0) {
      try {
        await ElMessageBox.confirm(`${day} 还没有日报，是否新建一篇？`, '新建日报', {
          confirmButtonText: '新建',
          cancelButtonText: '取消',
          type: 'info'
        })
      } catch {
        return
      }
      router.push({ path: '/daily/new', query: { work_date: day } })
      return
    }
    if (dayDetail.entries.length === 1 && dayDetail.entries[0].status === 'draft') {
      router.push(`/daily/${dayDetail.entries[0].id}`)
      return
    }
    router.push({ name: 'daily-day', params: { date: day } })
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    resolvingDate.value = false
  }
}

async function loadMonth(): Promise<void> {
  monthLoading.value = true
  try {
    const result = await getMonthSummary(month.value)
    monthItems.value = result.items
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    monthLoading.value = false
  }
}

watch(month, () => void loadMonth(), { immediate: true })

function monthBounds(): { from: string; to: string } {
  const year = calendarDate.value.getFullYear()
  const monthIndex = calendarDate.value.getMonth()
  return {
    from: formatCalendarDate(new Date(year, monthIndex, 1)),
    to: formatCalendarDate(new Date(year, monthIndex + 1, 0))
  }
}

async function exportMonth(): Promise<void> {
  const { from, to } = monthBounds()
  await runExport({ filter: { date_from: from, date_to: to, status: 'archived' } })
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

onMounted(() => {
  void loadMonth()
})
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">MY DAILY REPORTS</span>
        <h1>我的日报</h1>
        <p>
          按月历查看每天的日报状态；一天可创建多篇条目，提交后由你手动发起当天归档，归档后自动汇总为一份正式日报。点击某一天可进入该天的日报详情。
        </p>
      </div>
      <el-button :loading="exporting" @click="exportMonth">导出本月已归档日报</el-button>
    </header>

    <section class="calendar-legend">
      <el-tag
        v-for="status in legendStatuses"
        :key="status"
        :type="dayCellStatusTagType(status)"
        effect="plain"
      >
        {{ dayCellStatusLabel(status) }}
      </el-tag>
    </section>

    <section v-loading="monthLoading || resolvingDate" class="calendar-card create-card">
      <el-calendar v-model="calendarDate">
        <template #header>
          <div class="calendar-toolbar">
            <div class="calendar-toolbar-nav">
              <el-button size="small" @click="shiftMonth(-1)">‹ 上个月</el-button>
              <strong class="calendar-title">{{ month }}</strong>
              <el-button size="small" @click="shiftMonth(1)">下个月 ›</el-button>
            </div>
            <el-button size="small" @click="goToday">回到今天</el-button>
          </div>
        </template>
        <template #date-cell="{ data }">
          <div
            class="day-cell"
            :class="[
              `day-cell-${dayCellStatus(itemsByDate.get(data.day))}`,
              {
                'day-cell-selected': data.day === selectedDate,
                'day-cell-outside-month': data.type !== 'current-month'
              }
            ]"
            @click="selectDate(data.day)"
          >
            <span class="day-cell-date">{{ Number(data.day.slice(8, 10)) }}</span>
            <span class="day-cell-status">{{
              dayCellStatusLabel(dayCellStatus(itemsByDate.get(data.day)))
            }}</span>
            <span v-if="itemsByDate.get(data.day)" class="day-cell-count">
              {{ itemsByDate.get(data.day)!.total_count }} 篇
            </span>
          </div>
        </template>
      </el-calendar>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import {
  generateWeeklyReport,
  getWeeklyAvailability,
  listWeeklyReports
} from '@renderer/api/weekly-reports'
import type {
  WeeklyAvailabilityData,
  WeeklyReportListItemData
} from '@renderer/types/weekly-report'
import { dailyStatusLabel, formatShanghaiTime } from '@renderer/utils/daily-form'
import {
  currentWeekStart,
  existingWeeklyReportId,
  mondayOfWeek
} from '@renderer/utils/weekly-report'

const router = useRouter()

const pickedDate = ref(currentWeekStart())
const availability = ref<WeeklyAvailabilityData | null>(null)
const availabilityLoading = ref(false)
const generating = ref(false)

const filterFrom = ref<string | null>(null)
const filterTo = ref<string | null>(null)
const items = ref<WeeklyReportListItemData[]>([])
const listLoading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  void loadAvailability()
  void loadList()
})

function statusTagType(value: string | null): 'warning' | 'success' | 'info' {
  if (value === null) {
    return 'info'
  }
  return { draft: 'warning' as const, submitted: 'success' as const, archived: 'info' as const }[
    value as 'draft' | 'submitted' | 'archived'
  ]
}

function statusLabel(value: string | null): string {
  return value === null ? '无日报' : dailyStatusLabel(value as 'draft' | 'submitted' | 'archived')
}

async function onWeekPick(): Promise<void> {
  pickedDate.value = mondayOfWeek(pickedDate.value)
  await loadAvailability()
}

async function loadAvailability(): Promise<void> {
  availabilityLoading.value = true
  try {
    availability.value = await getWeeklyAvailability(mondayOfWeek(pickedDate.value))
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    availabilityLoading.value = false
  }
}

async function loadList(nextPage = page.value): Promise<void> {
  listLoading.value = true
  try {
    const result = await listWeeklyReports({
      week_from: filterFrom.value ?? undefined,
      week_to: filterTo.value ?? undefined,
      page: nextPage,
      page_size: pageSize.value
    })
    items.value = result.items
    page.value = result.page
    total.value = result.total
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    listLoading.value = false
  }
}

function resetFilters(): void {
  filterFrom.value = null
  filterTo.value = null
  void loadList(1)
}

async function generateOrOpen(): Promise<void> {
  if (!availability.value) {
    return
  }
  if (availability.value.existing_weekly_report_id) {
    await router.push(`/weekly/${availability.value.existing_weekly_report_id}`)
    return
  }
  generating.value = true
  try {
    const report = await generateWeeklyReport(availability.value.week_start)
    await router.push(`/weekly/${report.id}`)
  } catch (error) {
    const existingId = existingWeeklyReportId(error)
    if (existingId) {
      ElMessage.info('该自然周周报已存在，已为你打开')
      await router.push(`/weekly/${existingId}`)
      return
    }
    ElMessage.error(userMessage(error))
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">WEEKLY WORKSPACE</span>
        <h1>周报工作台</h1>
        <p>按 Asia/Shanghai 自然周（周一至周日）汇总已归档日报，仅归档日报计入周报。</p>
      </div>
    </header>

    <section v-loading="availabilityLoading" class="create-card">
      <div class="create-card-copy">
        <span>自然周</span>
        <h2>选择这一周的任意一天</h2>
        <p>系统会自动定位到该周的周一至周日。</p>
      </div>
      <el-date-picker
        v-model="pickedDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        placeholder="选择日期"
        @change="onWeekPick"
      />
      <template v-if="availability">
        <p class="week-range">
          自然周：{{ availability.week_start }} 至 {{ availability.week_end }}
        </p>
        <div class="week-days">
          <el-tag
            v-for="day in availability.days"
            :key="day.work_date"
            :type="statusTagType(day.status)"
            effect="plain"
          >
            {{ day.work_date.slice(5) }} · {{ statusLabel(day.status) }}
          </el-tag>
        </div>
        <el-alert
          v-if="availability.non_archived_dates.length > 0"
          type="warning"
          :closable="false"
          show-icon
          :title="`以下日期的日报尚未归档，不会计入周报：${availability.non_archived_dates.join('、')}`"
        />
        <el-alert
          v-if="availability.archived_count === 0"
          type="info"
          :closable="false"
          show-icon
          title="本周暂无已归档日报，仍可生成一份空白周报。"
        />
      </template>
      <div class="create-card-actions">
        <el-button
          type="primary"
          :loading="generating"
          :disabled="!availability"
          @click="generateOrOpen"
        >
          {{ availability?.existing_weekly_report_id ? '查看本周周报' : '生成本周周报' }}
        </el-button>
      </div>
    </section>

    <section class="filter-card">
      <el-date-picker
        v-model="filterFrom"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        placeholder="开始周（含）"
      />
      <el-date-picker
        v-model="filterTo"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        placeholder="结束周（含）"
      />
      <el-button type="primary" plain @click="loadList(1)">筛选</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="table-card">
      <el-table
        v-loading="listLoading"
        :data="items"
        @row-click="(row) => router.push(`/weekly/${row.id}`)"
      >
        <el-table-column label="自然周" min-width="220">
          <template #default="scope">
            <strong class="report-date"
              >{{ scope.row.week_start }} 至 {{ scope.row.week_end }}</strong
            >
          </template>
        </el-table-column>
        <el-table-column label="生成时间" min-width="200">
          <template #default="scope">{{ formatShanghaiTime(scope.row.generated_at) }}</template>
        </el-table-column>
        <el-table-column label="最后更新" min-width="200">
          <template #default="scope">{{ formatShanghaiTime(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="版本" width="90">
          <template #default="scope">v{{ scope.row.version }}</template>
        </el-table-column>
        <el-table-column align="right" width="100">
          <template #default="scope">
            <el-button link type="primary" @click.stop="router.push(`/weekly/${scope.row.id}`)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-if="!listLoading && items.length === 0"
        description="暂无周报，先在上方生成一份"
      />
      <el-pagination
        v-if="total > 0"
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="loadList"
      />
    </section>
  </main>
</template>

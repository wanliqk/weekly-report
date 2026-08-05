<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { listDailyReports } from '@renderer/api/daily-reports'
import type {
  DailyReportListItemData,
  DailyReportQuery,
  DailyStatus
} from '@renderer/types/daily-report'
import { dailyStatusLabel, formatShanghaiTime } from '@renderer/utils/daily-form'

const router = useRouter()
const loading = ref(false)
const items = ref<DailyReportListItemData[]>([])
const dateRange = ref<[string, string] | null>(null)
const status = ref<DailyStatus | undefined>()
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => load())

async function load(nextPage = page.value): Promise<void> {
  loading.value = true
  try {
    const query: DailyReportQuery = {
      page: nextPage,
      page_size: pageSize.value
    }
    if (dateRange.value) {
      query.date_from = dateRange.value[0]
      query.date_to = dateRange.value[1]
    }
    if (status.value) {
      query.status = status.value
    }
    const result = await listDailyReports(query)
    items.value = result.items
    page.value = result.page
    total.value = result.total
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

function resetFilters(): void {
  dateRange.value = null
  status.value = undefined
  void load(1)
}

function statusTagType(value: DailyStatus): 'warning' | 'success' | 'info' {
  const types: Record<DailyStatus, 'warning' | 'success' | 'info'> = {
    draft: 'warning',
    submitted: 'success',
    archived: 'info'
  }
  return types[value]
}
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">DAILY WORKSPACE</span>
        <h1>日报工作台</h1>
        <p>按工作日期创建一份日报，草稿可持续保存，提交后可按个人设置自动归档。</p>
      </div>
      <el-button type="primary" @click="router.push('/daily/new')">新建日报</el-button>
    </header>

    <section class="filter-card">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <el-select v-model="status" clearable placeholder="全部状态">
        <el-option label="草稿" value="draft" />
        <el-option label="已提交" value="submitted" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-button type="primary" plain @click="load(1)">筛选</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="table-card">
      <el-table
        v-loading="loading"
        :data="items"
        @row-click="(row) => router.push(`/daily/${row.id}`)"
      >
        <el-table-column prop="work_date" label="工作日期" min-width="160">
          <template #default="scope">
            <strong class="report-date">{{ scope.row.work_date }}</strong>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="plain">
              {{ dailyStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后更新" min-width="210">
          <template #default="scope">{{ formatShanghaiTime(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="版本" width="90">
          <template #default="scope">v{{ scope.row.version }}</template>
        </el-table-column>
        <el-table-column align="right" width="100">
          <template #default="scope">
            <el-button link type="primary" @click.stop="router.push(`/daily/${scope.row.id}`)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && items.length === 0" description="暂无符合条件的日报" />
      <el-pagination
        v-if="total > 0"
        class="table-pagination"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="load"
      />
    </section>
  </main>
</template>

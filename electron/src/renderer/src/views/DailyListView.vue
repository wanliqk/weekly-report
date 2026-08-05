<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { listDailyReports } from '@renderer/api/daily-reports'
import { createDailyReportExport, downloadDailyReportExportFile } from '@renderer/api/exports'
import type {
  DailyReportListItemData,
  DailyReportQuery,
  DailyStatus
} from '@renderer/types/daily-report'
import type { ExportCreateRequest } from '@renderer/types/export'
import { dailyStatusLabel, formatShanghaiTime } from '@renderer/utils/daily-form'
import { invalidExportReportIds } from '@renderer/utils/export'

const router = useRouter()
const loading = ref(false)
const items = ref<DailyReportListItemData[]>([])
const dateRange = ref<[string, string] | null>(null)
const status = ref<DailyStatus | undefined>()
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedIds = ref<string[]>([])
const exporting = ref(false)

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

function describeReportId(id: string): string {
  return items.value.find((item) => item.id === id)?.work_date ?? id
}

async function exportSelected(): Promise<void> {
  if (selectedIds.value.length === 0) {
    return
  }
  await runExport({ report_ids: [...selectedIds.value] })
}

async function exportByCurrentFilter(): Promise<void> {
  await runExport({
    filter: {
      status: 'archived',
      ...(dateRange.value ? { date_from: dateRange.value[0], date_to: dateRange.value[1] } : {})
    }
  })
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
      ElMessage.warning('所选或筛选范围内没有可导出的归档日报')
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
    const invalidIds = invalidExportReportIds(error)
    if (invalidIds && invalidIds.length > 0) {
      ElMessage.error(
        `以下日报不可导出（需为本人已归档日报）：${invalidIds.map(describeReportId).join('、')}`
      )
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

    <section class="export-toolbar">
      <el-button :disabled="selectedIds.length === 0" :loading="exporting" @click="exportSelected">
        导出所选（{{ selectedIds.length }}）
      </el-button>
      <el-button :loading="exporting" @click="exportByCurrentFilter">
        导出当前筛选（仅归档）
      </el-button>
      <span class="export-hint">仅本人已归档日报可导出；未归档记录会被整体拒绝并提示</span>
    </section>

    <section class="table-card">
      <el-table
        v-loading="loading"
        :data="items"
        row-key="id"
        @row-click="(row, column) => column.type !== 'selection' && router.push(`/daily/${row.id}`)"
        @selection-change="
          (rows: DailyReportListItemData[]) => (selectedIds = rows.map((row) => row.id))
        "
      >
        <el-table-column type="selection" width="48" />
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

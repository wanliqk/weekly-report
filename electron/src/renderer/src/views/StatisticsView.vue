<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { userMessage } from '@renderer/api/client'
import { getMonthlyStatistics } from '@renderer/api/statistics'
import type { StatisticsMonthlyData } from '@renderer/types/statistics'
import {
  currentMonthInShanghai,
  dayCellStatus,
  dayCellStatusLabel,
  dayCellStatusTagType
} from '@renderer/utils/daily-report-day'
import { formatCompletionRate } from '@renderer/utils/statistics'

const router = useRouter()

const calendarDate = ref(parseMonth(currentMonthInShanghai()))
const stats = ref<StatisticsMonthlyData | null>(null)
const loading = ref(false)

const month = computed(() => formatMonth(calendarDate.value))
const itemsByDate = computed(
  () => new Map((stats.value?.days ?? []).map((item) => [item.work_date, item]))
)

function formatMonth(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function parseMonth(value: string): Date {
  const [year, monthNumber] = value.split('-').map(Number)
  return new Date(year, monthNumber - 1, 1)
}

function shiftMonth(delta: number): void {
  calendarDate.value = new Date(
    calendarDate.value.getFullYear(),
    calendarDate.value.getMonth() + delta,
    1
  )
}

function goToCurrentMonth(): void {
  calendarDate.value = parseMonth(currentMonthInShanghai())
}

function openDate(day: string): void {
  router.push({ path: '/daily', query: { date: day } })
}

async function load(): Promise<void> {
  loading.value = true
  try {
    stats.value = await getMonthlyStatistics(month.value)
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

watch(month, () => void load(), { immediate: true })

onMounted(() => void load())
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">STATISTICS</span>
        <h1>统计</h1>
        <p>仅统计你自己范围内的日报和周报数据，不包含其他账号。</p>
      </div>
    </header>

    <section v-loading="loading" class="dashboard-grid stats-grid">
      <article class="feature-card">
        <span>完成率</span>
        <h2>{{ formatCompletionRate(stats?.completion_rate ?? null) }}</h2>
        <p v-if="stats">
          {{ stats.completed_days }} / {{ stats.denominator_days }} 天完成（{{
            stats.effective_date_from
          }}
          至 {{ stats.effective_date_to }}）
        </p>
      </article>
      <article class="feature-card">
        <span>已写日报</span>
        <h2>{{ stats?.daily_report_count ?? 0 }} 篇</h2>
        <p>本月已提交/已归档的来源条目数，草稿不计入。</p>
      </article>
      <article class="feature-card">
        <span>已写周报</span>
        <h2>{{ stats?.weekly_report_count ?? 0 }} 篇</h2>
        <p>按周报所属自然周的起始日期归属到本月。</p>
      </article>
      <article class="feature-card">
        <span>当前连续记录</span>
        <h2>{{ stats?.current_streak_days ?? 0 }} 天</h2>
        <p>与所选月份无关：今天已完成则从今天算起，否则看昨天是否完成。</p>
      </article>
    </section>

    <section class="calendar-legend">
      <el-tag
        v-for="status in ['draft', 'submitted', 'mixed', 'archived'] as const"
        :key="status"
        :type="dayCellStatusTagType(status)"
        effect="plain"
      >
        {{ dayCellStatusLabel(status) }}
      </el-tag>
    </section>

    <section class="calendar-card create-card">
      <el-calendar v-model="calendarDate">
        <template #header>
          <div class="calendar-toolbar">
            <div class="calendar-toolbar-nav">
              <el-button size="small" @click="shiftMonth(-1)">‹ 上个月</el-button>
              <strong class="calendar-title">{{ month }}</strong>
              <el-button size="small" @click="shiftMonth(1)">下个月 ›</el-button>
            </div>
            <el-button size="small" @click="goToCurrentMonth">回到本月</el-button>
          </div>
        </template>
        <template #date-cell="{ data }">
          <div
            class="day-cell"
            :class="[
              `day-cell-${dayCellStatus(itemsByDate.get(data.day))}`,
              { 'day-cell-outside-month': data.type !== 'current-month' }
            ]"
            @click="openDate(data.day)"
          >
            <span class="day-cell-date">{{ Number(data.day.slice(8, 10)) }}</span>
            <span class="day-cell-status">{{
              dayCellStatusLabel(dayCellStatus(itemsByDate.get(data.day)))
            }}</span>
          </div>
        </template>
      </el-calendar>
    </section>
  </main>
</template>

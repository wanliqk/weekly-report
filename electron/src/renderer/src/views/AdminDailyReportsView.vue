<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import {
  listAuditEvents,
  listSubmittedDailyReports,
  revokeDailyReportSubmission
} from '@renderer/api/admin-daily-reports'
import { userMessage } from '@renderer/api/client'
import type {
  AdminAuditAction,
  AdminAuditEventData,
  AdminDailyReportSubmittedItemData
} from '@renderer/types/admin-daily-report'
import { auditActionLabel } from '@renderer/utils/admin'
import { formatShanghaiTime } from '@renderer/utils/daily-form'

const activeTab = ref<'submitted' | 'audit'>('submitted')

const submittedItems = ref<AdminDailyReportSubmittedItemData[]>([])
const submittedLoading = ref(false)
const submittedPage = ref(1)
const submittedTotal = ref(0)
const pageSize = 20

const revokeDialogVisible = ref(false)
const revokeTarget = ref<AdminDailyReportSubmittedItemData | null>(null)
const revokeReason = ref('')
const revoking = ref(false)

const auditItems = ref<AdminAuditEventData[]>([])
const auditLoading = ref(false)
const auditPage = ref(1)
const auditTotal = ref(0)
const auditFilter = reactive<{
  action: AdminAuditAction | undefined
  dateRange: [string, string] | null
}>({
  action: undefined,
  dateRange: null
})

async function loadSubmitted(nextPage = submittedPage.value): Promise<void> {
  submittedLoading.value = true
  try {
    const result = await listSubmittedDailyReports(nextPage, pageSize)
    submittedItems.value = result.items
    submittedPage.value = result.page
    submittedTotal.value = result.total
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    submittedLoading.value = false
  }
}

function openRevoke(item: AdminDailyReportSubmittedItemData): void {
  revokeTarget.value = item
  revokeReason.value = ''
  revokeDialogVisible.value = true
}

async function submitRevoke(): Promise<void> {
  const target = revokeTarget.value
  if (!target) return
  revoking.value = true
  try {
    await revokeDailyReportSubmission(target.id, target.version, revokeReason.value)
    ElMessage.success('已撤销该条目的提交')
    revokeDialogVisible.value = false
    await loadSubmitted()
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    revoking.value = false
  }
}

async function loadAudit(nextPage = auditPage.value): Promise<void> {
  auditLoading.value = true
  try {
    const result = await listAuditEvents({
      action: auditFilter.action,
      date_from: auditFilter.dateRange?.[0],
      date_to: auditFilter.dateRange?.[1],
      page: nextPage,
      page_size: pageSize
    })
    auditItems.value = result.items
    auditPage.value = result.page
    auditTotal.value = result.total
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    auditLoading.value = false
  }
}

function resetAuditFilters(): void {
  auditFilter.action = undefined
  auditFilter.dateRange = null
  void loadAudit(1)
}

onMounted(() => {
  void loadSubmitted()
  void loadAudit()
})
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">ADMINISTRATION</span>
        <h1>日报管理</h1>
        <p>
          只能查看待归档条目的必要元数据（账号、日期、版本、提交时间），不能查看任何用户的日报正文。
        </p>
      </div>
    </header>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="待归档条目" name="submitted">
        <section class="table-card">
          <el-table v-loading="submittedLoading" :data="submittedItems" row-key="id">
            <el-table-column label="账号" min-width="200">
              <template #default="scope">
                <div class="user-cell">
                  <div>
                    <strong>{{ scope.row.owner_display_name }}</strong>
                    <small>@{{ scope.row.owner_username }}</small>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="work_date" label="工作日期" width="140" />
            <el-table-column label="提交时间" min-width="200">
              <template #default="scope">{{ formatShanghaiTime(scope.row.submitted_at) }}</template>
            </el-table-column>
            <el-table-column label="版本" width="90">
              <template #default="scope">v{{ scope.row.version }}</template>
            </el-table-column>
            <el-table-column align="right" width="120">
              <template #default="scope">
                <el-button link type="danger" @click="openRevoke(scope.row)">撤销提交</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty
            v-if="!submittedLoading && submittedItems.length === 0"
            description="当前没有待归档的日报条目"
          />
          <el-pagination
            v-if="submittedTotal > pageSize"
            class="table-pagination"
            layout="prev, pager, next, total"
            :current-page="submittedPage"
            :page-size="pageSize"
            :total="submittedTotal"
            @current-change="loadSubmitted"
          />
        </section>
      </el-tab-pane>

      <el-tab-pane label="审计记录" name="audit">
        <section class="filter-card">
          <el-select v-model="auditFilter.action" clearable placeholder="全部动作">
            <el-option label="撤销日报提交" value="daily_submission_revoked" />
            <el-option label="删除用户" value="user_deleted" />
          </el-select>
          <el-date-picker
            v-model="auditFilter.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
          <el-button type="primary" plain @click="loadAudit(1)">筛选</el-button>
          <el-button @click="resetAuditFilters">重置</el-button>
        </section>

        <section class="table-card">
          <el-table v-loading="auditLoading" :data="auditItems" row-key="id">
            <el-table-column label="动作" width="140">
              <template #default="scope">
                <el-tag effect="plain">{{ auditActionLabel(scope.row.action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作者" width="140" prop="actor_username_snapshot" />
            <el-table-column label="目标" min-width="200">
              <template #default="scope"
                >{{ scope.row.target_type }} · {{ scope.row.target_id }}</template
              >
            </el-table-column>
            <el-table-column label="原因" min-width="220" prop="reason" show-overflow-tooltip />
            <el-table-column label="时间" min-width="200">
              <template #default="scope">{{ formatShanghaiTime(scope.row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!auditLoading && auditItems.length === 0" description="暂无审计记录" />
          <el-pagination
            v-if="auditTotal > pageSize"
            class="table-pagination"
            layout="prev, pager, next, total"
            :current-page="auditPage"
            :page-size="pageSize"
            :total="auditTotal"
            @current-change="loadAudit"
          />
        </section>
      </el-tab-pane>
    </el-tabs>
  </main>

  <el-dialog v-model="revokeDialogVisible" title="撤销日报提交" width="460px">
    <p class="dialog-copy">
      将 {{ revokeTarget?.owner_display_name }}（@{{ revokeTarget?.owner_username }}） 于
      {{ revokeTarget?.work_date }} 提交的这份条目撤回为草稿。撤销后正文保留，所有者将看到撤销原因。
    </p>
    <el-form label-position="top">
      <el-form-item label="撤销原因">
        <el-input v-model="revokeReason" type="textarea" :rows="3" maxlength="500" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="revokeDialogVisible = false">取消</el-button>
      <el-button
        type="danger"
        :loading="revoking"
        :disabled="revokeReason.trim().length === 0"
        @click="submitRevoke"
        >确认撤销</el-button
      >
    </template>
  </el-dialog>
</template>

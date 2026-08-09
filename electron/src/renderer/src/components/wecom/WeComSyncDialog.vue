<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, reactive, ref, watch } from 'vue'

import { userMessage } from '@renderer/api/client'
import {
  createOrGetWeComDaySync,
  createWeComPreview,
  getWeComConnection,
  getWeComProfile,
  getWeComSyncRecord,
  listWeComSyncRecords,
  retryWeComSyncRecord,
  updateWeComProfile
} from '@renderer/api/wecom'
import type {
  WeComConnectionData,
  WeComFieldMappingTarget,
  WeComPreviewData,
  WeComProfileData,
  WeComSyncRecordData
} from '@renderer/types/wecom'
import { formatShanghaiTime } from '@renderer/utils/daily-form'
import {
  upsertWeComFieldMappingRule,
  weComSyncIsRetryEligible,
  weComSyncStatusLabel,
  weComSyncStatusTagType,
  weComSyncSummary
} from '@renderer/utils/wecom'

const props = defineProps<{
  modelValue: boolean
  dailyReportDayId: string
  workDate: string
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const loading = ref(false)
const running = ref(false)
const savingMappings = ref(false)
const connection = ref<WeComConnectionData | null>(null)
const profile = ref<WeComProfileData | null>(null)
const preview = ref<WeComPreviewData | null>(null)
const record = ref<WeComSyncRecordData | null>(null)
const unmappedTargets = reactive<Record<string, WeComFieldMappingTarget | 'unmapped'>>({})

const hasBlockingUnmappedFields = computed(
  () =>
    profile.value?.field_mapping.unmapped_policy === 'block' &&
    (preview.value?.unmapped_field_keys.length ?? 0) > 0
)

const primaryActionLabel = computed(() => {
  if (!record.value || record.value.status === 'pending') {
    return '确认同步'
  }
  if (weComSyncIsRetryEligible(record.value.status)) {
    return '确认重试'
  }
  if (record.value.status === 'syncing') {
    return '同步中'
  }
  if (record.value.status === 'succeeded') {
    return '已同步'
  }
  return '暂不可同步'
})

const primaryActionDisabled = computed(
  () =>
    loading.value ||
    running.value ||
    connection.value?.connected !== true ||
    preview.value === null ||
    hasBlockingUnmappedFields.value ||
    record.value?.status === 'syncing' ||
    record.value?.status === 'succeeded' ||
    record.value?.status === 'uncertain'
)

watch(
  () => props.modelValue,
  (isVisible) => {
    if (isVisible) {
      void loadDialog()
    }
  }
)

function resetUnmappedTargets(keys: string[]): void {
  for (const key of Object.keys(unmappedTargets)) {
    delete unmappedTargets[key]
  }
  for (const key of keys) {
    unmappedTargets[key] = 'unmapped'
  }
}

async function loadDialog(): Promise<void> {
  loading.value = true
  preview.value = null
  profile.value = null
  record.value = null
  try {
    connection.value = await getWeComConnection()
    if (!connection.value.connected) {
      return
    }
    const [loadedPreview, loadedProfile, records] = await Promise.all([
      createWeComPreview(props.dailyReportDayId),
      getWeComProfile(),
      listWeComSyncRecords({
        date_from: props.workDate,
        date_to: props.workDate,
        page: 1,
        page_size: 20
      })
    ])
    preview.value = loadedPreview
    profile.value = loadedProfile
    record.value =
      records.items.find((item) => item.daily_report_day_id === props.dailyReportDayId) ?? null
    resetUnmappedTargets(loadedPreview.unmapped_field_keys)
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

async function saveUnmappedFields(): Promise<void> {
  if (!profile.value || !preview.value) {
    return
  }
  const missing = preview.value.unmapped_field_keys.filter(
    (fieldKey) => unmappedTargets[fieldKey] === 'unmapped'
  )
  if (missing.length > 0) {
    ElMessage.warning('请为全部未映射字段选择目标或明确忽略')
    return
  }

  let rules = [...profile.value.field_mapping.rules]
  for (const fieldKey of preview.value.unmapped_field_keys) {
    const target = unmappedTargets[fieldKey]
    if (target === 'unmapped') {
      continue
    }
    rules = upsertWeComFieldMappingRule(rules, fieldKey, target)
  }

  savingMappings.value = true
  try {
    await updateWeComProfile({
      expected_version: profile.value.version,
      field_mapping: {
        ...profile.value.field_mapping,
        rules
      }
    })
    ElMessage.success('字段映射已保存，正在重新生成预览')
    await loadDialog()
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    savingMappings.value = false
  }
}

async function runSync(): Promise<void> {
  if (primaryActionDisabled.value) {
    return
  }
  const confirmationMessage =
    record.value?.status === 'auth_required'
      ? `请确认已在设置中重新登录企业微信，再重试 ${props.workDate} 的同步。`
      : record.value?.status === 'schema_changed'
        ? `请确认已在设置中重新连接并核对最新模板映射，再重试 ${props.workDate} 的同步。`
        : record.value?.status === 'duplicate_detected'
          ? `请先在企业微信中核对 ${props.workDate} 没有已生成的日报，再确认重试。`
          : `确认将 ${props.workDate} 的日期级正式日报按当前预览同步到企业微信吗？`
  try {
    await ElMessageBox.confirm(confirmationMessage, '确认同步', {
      confirmButtonText: '确认同步',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  running.value = true
  try {
    let current = await createOrGetWeComDaySync(props.workDate)
    if (current.status === 'succeeded') {
      record.value = current
      ElMessage.success('该正式日报已经同步，无需重复提交')
      return
    }
    if (current.status === 'uncertain') {
      record.value = current
      ElMessage.warning('上次同步结果不确定，请先在企业微信核对，系统不会自动重试')
      return
    }
    if (weComSyncIsRetryEligible(current.status)) {
      current = { ...(await retryWeComSyncRecord(current.id)), created: false }
    }
    record.value = current
    if (current.status === 'syncing') {
      ElMessage.info('同步正在处理中，请稍后刷新状态')
      return
    }

    const outcome = await window.runtimeBridge.wecom.executeSync(current.id)
    record.value = await getWeComSyncRecord(current.id)
    if (outcome.status === 'failed') {
      ElMessage.error(record.value.last_error_message ?? outcome.reason ?? '同步失败')
      return
    }
    if (record.value.status === 'succeeded') {
      ElMessage.success('已成功同步到企业微信')
    } else {
      ElMessage.warning(weComSyncSummary(record.value))
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    running.value = false
  }
}

async function refreshRecord(): Promise<void> {
  if (!record.value) {
    await loadDialog()
    return
  }
  try {
    record.value = await getWeComSyncRecord(record.value.id)
  } catch (error) {
    ElMessage.error(userMessage(error))
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="同步到企业微信" width="760px" destroy-on-close>
    <div v-loading="loading" class="wecom-sync-dialog">
      <el-alert
        v-if="connection && !connection.connected"
        title="企业微信尚未连接或登录已失效，请先到“设置”中连接。"
        type="warning"
        :closable="false"
        show-icon
      />

      <template v-if="preview">
        <div class="wecom-preview-summary">
          <el-tag effect="plain">{{ preview.date_answer }}</el-tag>
          <span>{{ preview.source_count }} 篇来源</span>
          <span>今日 {{ preview.today_work_char_count }} 字</span>
          <span>明日 {{ preview.tomorrow_plan_char_count }} 字</span>
        </div>

        <section class="wecom-preview-section">
          <h3>今日工作内容</h3>
          <pre>{{ preview.today_work_answer || '（空）' }}</pre>
        </section>
        <section class="wecom-preview-section">
          <h3>明日工作计划</h3>
          <pre>{{ preview.tomorrow_plan_answer || '（空）' }}</pre>
        </section>

        <el-alert
          v-if="preview.unmapped_field_keys.length > 0"
          :title="
            hasBlockingUnmappedFields
              ? '存在未映射的非空历史字段，保存映射后才能同步。'
              : '存在未映射字段；当前配置会忽略它们，建议仍明确映射。'
          "
          :type="hasBlockingUnmappedFields ? 'error' : 'warning'"
          :closable="false"
          show-icon
        />
        <div v-if="preview.unmapped_field_keys.length > 0" class="wecom-unmapped-list">
          <div
            v-for="fieldKey in preview.unmapped_field_keys"
            :key="fieldKey"
            class="wecom-unmapped-row"
          >
            <code>{{ fieldKey }}</code>
            <el-select v-model="unmappedTargets[fieldKey]" size="small">
              <el-option label="请选择" value="unmapped" />
              <el-option label="今日工作内容" value="today_work" />
              <el-option label="明日工作计划" value="tomorrow_plan" />
              <el-option label="忽略" value="ignore" />
            </el-select>
          </div>
          <el-button :loading="savingMappings" @click="saveUnmappedFields">保存字段映射</el-button>
        </div>

        <div v-if="record" class="wecom-current-record">
          <div>
            <span>当前状态</span>
            <el-tag :type="weComSyncStatusTagType(record.status)" effect="plain">
              {{ weComSyncStatusLabel(record.status) }}
            </el-tag>
          </div>
          <p>{{ weComSyncSummary(record) }}</p>
          <p v-if="record.last_attempt_at">
            最近尝试：{{ formatShanghaiTime(record.last_attempt_at) }} · 共
            {{ record.attempt_count }} 次
          </p>
          <el-button link type="primary" @click="refreshRecord">刷新状态</el-button>
        </div>

        <el-alert
          v-if="record?.status === 'uncertain'"
          title="结果不确定时禁止直接重试。请先在企业微信中核对当天是否已生成日报。"
          type="warning"
          :closable="false"
          show-icon
        />
      </template>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button
        type="primary"
        :loading="running"
        :disabled="primaryActionDisabled"
        @click="runSync"
      >
        {{ primaryActionLabel }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.wecom-sync-dialog {
  min-height: 160px;
}

.wecom-preview-summary,
.wecom-unmapped-row,
.wecom-current-record > div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.wecom-preview-summary {
  margin-bottom: 16px;
  color: var(--el-text-color-secondary);
}

.wecom-preview-section {
  margin-bottom: 16px;
}

.wecom-preview-section h3 {
  margin: 0 0 8px;
  font-size: 15px;
}

.wecom-preview-section pre {
  max-height: 240px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font: inherit;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.wecom-unmapped-list,
.wecom-current-record {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.wecom-unmapped-row code {
  flex: 1;
}

.wecom-unmapped-row .el-select {
  width: 220px;
}

.wecom-current-record p {
  margin: 0;
  color: var(--el-text-color-secondary);
}
</style>

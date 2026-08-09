<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, userMessage } from '@renderer/api/client'
import { getCurrentTemplate } from '@renderer/api/templates'
import {
  getWeComConnection,
  getWeComProfile,
  listWeComSyncRecords,
  retryWeComSyncRecord,
  updateWeComProfile
} from '@renderer/api/wecom'
import type { TemplateFieldData } from '@renderer/types/template'
import type {
  WeComConnectionData,
  WeComFieldMappingRule,
  WeComFieldMappingTarget,
  WeComProfileData,
  WeComSyncRecordData,
  WeComSyncStatus,
  WeComUnmappedFieldPolicy
} from '@renderer/types/wecom'
import { formatShanghaiTime } from '@renderer/utils/daily-form'
import {
  parseWeComFormId,
  replaceVisibleWeComFieldMappingRules,
  weComFieldMappingRuleTarget,
  weComMappableTemplateFields,
  weComSyncActionLabel,
  weComSyncStatusLabel,
  weComSyncStatusTagType,
  weComSyncSummary
} from '@renderer/utils/wecom'

const props = defineProps<{ enabled: boolean }>()
const router = useRouter()

const loading = ref(false)
const connection = ref<WeComConnectionData | null>(null)
const profile = ref<WeComProfileData | null>(null)
const mappableFields = ref<TemplateFieldData[]>([])
const syncRecords = ref<WeComSyncRecordData[]>([])
const syncRecordsLoading = ref(false)
const syncRecordStatus = ref<WeComSyncStatus | ''>('')
const syncRecordPage = ref(1)
const syncRecordTotal = ref(0)

const formUrlInput = ref('')
const connecting = ref(false)
const disconnecting = ref(false)

const mngreporterVids = ref<string[]>([])
const reporterVids = ref<string[]>([])
const unmappedPolicy = ref<WeComUnmappedFieldPolicy>('block')
const fieldTargets = reactive<Record<string, WeComFieldMappingTarget | 'unmapped'>>({})
const savingMapping = ref(false)

const retryingRecordId = ref<string | null>(null)

const hasEverConnected = computed(
  () => connection.value !== null && connection.value.status !== null
)
const isConnected = computed(() => connection.value?.connected === true)

watch(
  () => props.enabled,
  (enabled) => {
    if (enabled) {
      void load()
    }
  },
  { immediate: true }
)

async function load(): Promise<void> {
  loading.value = true
  try {
    connection.value = await getWeComConnection()
    if (connection.value.status !== null) {
      await Promise.all([loadProfile(), loadSyncRecords()])
    } else {
      profile.value = null
      syncRecords.value = []
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

async function loadProfile(): Promise<void> {
  try {
    const [loadedProfile, currentTemplate] = await Promise.all([
      getWeComProfile(),
      getCurrentTemplate()
    ])
    profile.value = loadedProfile
    mappableFields.value = weComMappableTemplateFields(currentTemplate.fields)
    resetMappingForm(loadedProfile)
  } catch (error) {
    if (error instanceof ApiError && error.code === 40911) {
      profile.value = null
      return
    }
    ElMessage.error(userMessage(error))
  }
}

function resetMappingForm(loadedProfile: WeComProfileData): void {
  mngreporterVids.value = [...loadedProfile.recipient_config.mngreporter_vids]
  reporterVids.value = [...loadedProfile.recipient_config.reporter_vids]
  unmappedPolicy.value = loadedProfile.field_mapping.unmapped_policy
  for (const key of Object.keys(fieldTargets)) {
    delete fieldTargets[key]
  }
  for (const field of mappableFields.value) {
    fieldTargets[field.field_key] =
      weComFieldMappingRuleTarget(loadedProfile.field_mapping.rules, field.field_key) ?? 'unmapped'
  }
}

async function loadSyncRecords(): Promise<void> {
  syncRecordsLoading.value = true
  try {
    const result = await listWeComSyncRecords({
      status: syncRecordStatus.value || undefined,
      page: syncRecordPage.value,
      page_size: 10
    })
    syncRecords.value = result.items
    syncRecordTotal.value = result.total
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    syncRecordsLoading.value = false
  }
}

async function connect(): Promise<void> {
  const formId = parseWeComFormId(formUrlInput.value)
  if (!formId) {
    ElMessage.warning('请输入有效的企业微信日报表单链接或表单 ID')
    return
  }
  connecting.value = true
  try {
    const result = await window.runtimeBridge.wecom.connect(formId)
    if (result.status === 'connected') {
      if (result.reason) {
        ElMessage.warning(result.reason)
      } else {
        ElMessage.success('企业微信连接成功')
      }
      formUrlInput.value = ''
      await load()
    } else if (result.status === 'canceled') {
      ElMessage.info('已取消登录')
    } else {
      ElMessage.error(result.reason ?? '连接企业微信失败')
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    connecting.value = false
  }
}

async function disconnect(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '断开后需要重新登录企业微信才能继续同步，已同步的历史记录不受影响。',
      '断开企业微信连接',
      { confirmButtonText: '确认断开', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  disconnecting.value = true
  try {
    const result = await window.runtimeBridge.wecom.disconnect()
    if (result.status === 'disconnected') {
      ElMessage.success('已断开企业微信连接')
      await load()
    } else {
      ElMessage.error(result.reason ?? '断开连接失败')
    }
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    disconnecting.value = false
  }
}

async function saveMapping(): Promise<void> {
  if (!profile.value) {
    return
  }
  const rules: WeComFieldMappingRule[] = replaceVisibleWeComFieldMappingRules(
    profile.value.field_mapping.rules,
    mappableFields.value.map((field) => field.field_key),
    fieldTargets
  )
  const normalizedMngreporterVids = normalizeVids(mngreporterVids.value)
  const normalizedReporterVids = normalizeVids(reporterVids.value)
  if (normalizedMngreporterVids.length === 0 && normalizedReporterVids.length === 0) {
    ElMessage.warning('请至少配置一个企业微信接收人 vid')
    return
  }
  savingMapping.value = true
  try {
    const updatedProfile = await updateWeComProfile({
      expected_version: profile.value.version,
      recipient_config: {
        schema_version: 1,
        mngreporter_vids: normalizedMngreporterVids,
        reporter_vids: normalizedReporterVids,
        remote_version: profile.value.recipient_config.remote_version
      },
      field_mapping: {
        schema_version: 1,
        rules,
        unmapped_policy: unmappedPolicy.value
      }
    })
    profile.value = updatedProfile
    resetMappingForm(updatedProfile)
    ElMessage.success('同步设置已保存')
  } catch (error) {
    if (error instanceof ApiError && error.code === 40904) {
      ElMessage.warning('设置已在别处更新，已重新加载最新配置')
      await loadProfile()
      return
    }
    ElMessage.error(userMessage(error))
  } finally {
    savingMapping.value = false
  }
}

function normalizeVids(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter((value) => value.length > 0))]
}

function changeSyncStatus(): void {
  syncRecordPage.value = 1
  void loadSyncRecords()
}

function openDailyRecord(record: WeComSyncRecordData): void {
  void router.push({ path: '/daily', query: { date: record.work_date } })
}

async function retry(record: WeComSyncRecordData): Promise<void> {
  if (!isConnected.value) {
    ElMessage.warning('请先重新连接企业微信，再重试同步')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认重试 ${record.work_date} 的同步吗？系统只允许明确未被远端受理的失败记录重试。`,
      '确认重试',
      { confirmButtonText: '确认重试', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  retryingRecordId.value = record.id
  try {
    await retryWeComSyncRecord(record.id)
    const outcome = await window.runtimeBridge.wecom.executeSync(record.id)
    await loadSyncRecords()
    if (outcome.status === 'failed') {
      ElMessage.error(outcome.reason ?? '重试失败')
    } else {
      ElMessage.success('已完成重试，请查看最新状态')
    }
  } catch (error) {
    await loadSyncRecords()
    ElMessage.error(userMessage(error))
  } finally {
    retryingRecordId.value = null
  }
}

async function executePending(record: WeComSyncRecordData): Promise<void> {
  if (!isConnected.value) {
    ElMessage.warning('请先重新连接企业微信，再继续同步')
    return
  }
  retryingRecordId.value = record.id
  try {
    const outcome = await window.runtimeBridge.wecom.executeSync(record.id)
    await loadSyncRecords()
    if (outcome.status === 'failed') {
      ElMessage.error(outcome.reason ?? '同步失败，记录仍可继续执行')
    } else {
      ElMessage.success('已提交同步，请查看最新状态')
    }
  } catch (error) {
    await loadSyncRecords()
    ElMessage.error(userMessage(error))
  } finally {
    retryingRecordId.value = null
  }
}

function runHistoryAction(record: WeComSyncRecordData): void {
  if (record.status === 'pending') {
    void executePending(record)
  } else if (record.status === 'failed') {
    void retry(record)
  }
}
</script>

<template>
  <div v-if="!enabled" class="editor-card">
    <div class="section-heading">
      <div>
        <span>WECOM</span>
        <h2>企业微信同步</h2>
      </div>
      <el-tag type="info" effect="plain">功能暂未开放</el-tag>
    </div>
    <p class="field-hint">
      企业微信同步入口仅作占位展示，当前版本不会连接企业微信或发起任何相关网络请求。
    </p>
    <el-button disabled>连接企业微信</el-button>
  </div>

  <div v-else v-loading="loading" class="editor-card wecom-settings-card">
    <div class="section-heading">
      <div>
        <span>WECOM</span>
        <h2>企业微信同步</h2>
      </div>
      <el-tag :type="isConnected ? 'success' : 'info'" effect="plain">
        {{ isConnected ? '已连接' : hasEverConnected ? '未连接' : '尚未连接' }}
      </el-tag>
    </div>

    <p v-if="connection?.connected" class="field-hint">
      当前账号：{{ connection.display_name || connection.wecom_vid }}
      <span v-if="connection.last_validated_at">
        · 最近校验：{{ formatShanghaiTime(connection.last_validated_at) }}</span
      >
    </p>
    <p v-else-if="hasEverConnected" class="field-hint">
      连接状态：{{ connection?.status === 'expired' ? '登录已失效，请重新连接' : '已断开' }}
    </p>

    <div class="wecom-connect-row">
      <el-input
        v-model="formUrlInput"
        placeholder="粘贴企业微信日报表单链接，或直接输入表单 ID"
        clearable
      />
      <el-button type="primary" :loading="connecting" @click="connect">
        {{ isConnected ? '重新连接' : '连接企业微信' }}
      </el-button>
      <el-button v-if="isConnected" :loading="disconnecting" @click="disconnect"
        >断开连接</el-button
      >
    </div>
    <p class="field-hint">
      地址形如 https://doc.weixin.qq.com/forms/j/表单ID...；也可直接粘贴表单
      ID。点击后会打开企业微信登录窗口，请在窗口内完成登录。
    </p>

    <template v-if="profile">
      <el-divider />
      <h3 class="wecom-subheading">字段映射</h3>
      <p class="field-hint">
        目标表单：{{ profile.form_id }} · 日报模板：{{ profile.template_id }}
      </p>
      <p class="field-hint">
        "今日工作内容""明日工作计划"和"项目列表"字段自动映射，无需配置；其余自定义字段需要指定映射目标，否则非空值会阻止同步。
      </p>
      <el-table :data="mappableFields" row-key="field_key" size="small">
        <el-table-column prop="label" label="字段" min-width="160" />
        <el-table-column label="映射目标" min-width="200">
          <template #default="scope">
            <el-select v-model="fieldTargets[scope.row.field_key as string]" size="small">
              <el-option label="未设置（有值时阻止同步）" value="unmapped" />
              <el-option label="今日工作内容" value="today_work" />
              <el-option label="明日工作计划" value="tomorrow_plan" />
              <el-option label="忽略" value="ignore" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="mappableFields.length === 0" description="当前模板没有需要映射的自定义字段" />

      <el-form label-position="top" class="wecom-mapping-form">
        <el-form-item label="未映射字段策略">
          <el-radio-group v-model="unmappedPolicy">
            <el-radio value="block">阻止同步（推荐）</el-radio>
            <el-radio value="ignore">静默忽略</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="管理者接收人 vid（mngreporter）">
          <el-select
            v-model="mngreporterVids"
            multiple
            filterable
            allow-create
            default-first-option
          >
            <el-option v-for="vid in mngreporterVids" :key="vid" :label="vid" :value="vid" />
          </el-select>
        </el-form-item>
        <el-form-item label="填报接收人 vid（reporter）">
          <el-select v-model="reporterVids" multiple filterable allow-create default-first-option>
            <el-option v-for="vid in reporterVids" :key="vid" :label="vid" :value="vid" />
          </el-select>
        </el-form-item>
        <span class="field-hint">
          vid
          是企业微信内部成员标识，无法在本应用内查询，请从原表单已提交记录或管理员处获取后手动输入，按
          Enter 添加。
        </span>
        <el-button type="primary" :loading="savingMapping" @click="saveMapping"
          >保存同步设置</el-button
        >
      </el-form>

      <el-divider />
      <div class="wecom-history-heading">
        <h3 class="wecom-subheading">同步历史</h3>
        <el-select
          v-model="syncRecordStatus"
          size="small"
          class="wecom-status-filter"
          @change="changeSyncStatus"
        >
          <el-option label="全部状态" value="" />
          <el-option label="待同步" value="pending" />
          <el-option label="同步中" value="syncing" />
          <el-option label="已同步" value="succeeded" />
          <el-option label="同步失败" value="failed" />
          <el-option label="登录已失效" value="auth_required" />
          <el-option label="模板结构已变化" value="schema_changed" />
          <el-option label="疑似重复" value="duplicate_detected" />
          <el-option label="结果不确定" value="uncertain" />
        </el-select>
      </div>
      <el-table v-loading="syncRecordsLoading" :data="syncRecords" size="small" row-key="id">
        <el-table-column prop="work_date" label="日期" width="120" />
        <el-table-column label="状态" width="140">
          <template #default="scope">
            <el-tag :type="weComSyncStatusTagType(scope.row.status)" effect="plain">
              {{ weComSyncStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="说明" min-width="220" show-overflow-tooltip>
          <template #default="scope">{{ weComSyncSummary(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180">
          <template #default="scope">{{ formatShanghaiTime(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column align="right" width="170">
          <template #default="scope">
            <el-button link @click="openDailyRecord(scope.row)">查看日报</el-button>
            <el-tooltip
              v-if="weComSyncActionLabel(scope.row.status)"
              :disabled="isConnected"
              content="请先重新连接企业微信"
              placement="top"
            >
              <span>
                <el-button
                  link
                  type="primary"
                  :disabled="!isConnected"
                  :loading="retryingRecordId === scope.row.id"
                  @click="runHistoryAction(scope.row)"
                >
                  {{ weComSyncActionLabel(scope.row.status) }}
                </el-button>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!syncRecordsLoading && syncRecords.length === 0" description="暂无同步记录" />
      <el-pagination
        v-if="syncRecordTotal > 10"
        v-model:current-page="syncRecordPage"
        class="wecom-pagination"
        layout="prev, pager, next, total"
        :page-size="10"
        :total="syncRecordTotal"
        @current-change="loadSyncRecords"
      />
    </template>
  </div>
</template>

<style scoped>
.wecom-connect-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.wecom-connect-row .el-input {
  flex: 1;
}

.wecom-subheading {
  margin: 0 0 8px;
  font-size: 15px;
}

.wecom-history-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.wecom-history-heading .wecom-subheading {
  margin-bottom: 0;
}

.wecom-status-filter {
  width: 180px;
}

.wecom-pagination {
  justify-content: flex-end;
  margin-top: 12px;
}

.wecom-mapping-form {
  max-width: 480px;
}
</style>

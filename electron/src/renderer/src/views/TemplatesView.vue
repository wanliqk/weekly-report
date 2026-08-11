<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'

import { userMessage } from '@renderer/api/client'
import { getCurrentTemplate, listTemplateVersions, publishTemplate } from '@renderer/api/templates'
import type { TemplateFieldType, TemplateVersionSummaryData } from '@renderer/types/template'
import {
  createTemplateFieldDraft,
  toTemplateFieldDrafts,
  toTemplateFieldPayload,
  type TemplateFieldDraft,
  usesOptions,
  validateTemplateFields
} from '@renderer/utils/template-fields'
import { formatShanghaiTime } from '@renderer/utils/daily-form'

const fieldTypeOptions: Array<{ value: TemplateFieldType; label: string }> = [
  { value: 'text', label: '单行文本' },
  { value: 'textarea', label: '多行文本' },
  { value: 'number', label: '数字' },
  { value: 'date', label: '日期' },
  { value: 'select', label: '单选' },
  { value: 'multiselect', label: '多选' },
  { value: 'PROJECT_LIST', label: '项目列表' }
]

const loading = ref(true)
const publishing = ref(false)
const templateName = ref('日报模板')
const currentVersion = ref(0)
const fields = ref<TemplateFieldDraft[]>([])
const versions = ref<TemplateVersionSummaryData[]>([])

onMounted(load)

async function load(): Promise<void> {
  loading.value = true
  try {
    const [template, history] = await Promise.all([getCurrentTemplate(), listTemplateVersions()])
    templateName.value = template.name
    currentVersion.value = template.version_no
    fields.value = toTemplateFieldDrafts(template.fields)
    versions.value = history.items
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    loading.value = false
  }
}

function addField(): void {
  fields.value.push(createTemplateFieldDraft())
}

function removeField(index: number): void {
  if (fields.value[index]?.core_type) {
    return
  }
  fields.value.splice(index, 1)
}

function moveField(index: number, offset: number): void {
  const target = index + offset
  if (target < 0 || target >= fields.value.length) {
    return
  }
  const [field] = fields.value.splice(index, 1)
  if (field) {
    fields.value.splice(target, 0, field)
  }
}

function handleTypeChange(field: TemplateFieldDraft): void {
  if (!usesOptions(field.field_type)) {
    field.options = []
  }
}

async function publish(): Promise<void> {
  const validationErrors = validateTemplateFields(fields.value)
  if (validationErrors.length > 0) {
    ElMessage.error(validationErrors[0])
    return
  }
  publishing.value = true
  try {
    const template = await publishTemplate(toTemplateFieldPayload(fields.value))
    const history = await listTemplateVersions()
    currentVersion.value = template.version_no
    fields.value = toTemplateFieldDrafts(template.fields)
    versions.value = history.items
    ElMessage.success(`模板 v${template.version_no} 已发布`)
  } catch (error) {
    ElMessage.error(userMessage(error))
  } finally {
    publishing.value = false
  }
}
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading">
      <div>
        <span class="eyebrow">TEMPLATE BUILDER</span>
        <h1>模板管理</h1>
        <p>发布会创建不可变的新版本；既有日报继续使用创建时保存的模板快照。</p>
      </div>
      <el-button type="primary" :loading="publishing" :disabled="loading" @click="publish">
        发布新版本
      </el-button>
    </header>

    <div v-loading="loading" class="template-layout">
      <section class="editor-card">
        <div class="section-heading">
          <div>
            <span>当前模板</span>
            <h2>{{ templateName }} · v{{ currentVersion }}</h2>
          </div>
          <el-button @click="addField">新增字段</el-button>
        </div>

        <el-empty v-if="!loading && fields.length === 0" description="模板暂无字段" />
        <div v-else class="template-fields">
          <article v-for="(field, index) in fields" :key="field.client_key" class="field-editor">
            <div class="field-editor-toolbar">
              <div>
                <strong>字段 {{ index + 1 }}</strong>
                <el-tag v-if="field.core_type" size="small" effect="plain">核心字段</el-tag>
              </div>
              <div>
                <el-button link :disabled="index === 0" @click="moveField(index, -1)"
                  >上移</el-button
                >
                <el-button
                  link
                  :disabled="index === fields.length - 1"
                  @click="moveField(index, 1)"
                >
                  下移
                </el-button>
                <el-button
                  link
                  type="danger"
                  :disabled="field.core_type !== null"
                  @click="removeField(index)"
                >
                  删除
                </el-button>
              </div>
            </div>

            <div class="field-editor-grid">
              <el-form-item label="字段名称" required>
                <el-input v-model="field.label" maxlength="100" />
              </el-form-item>
              <el-form-item label="字段类型" required>
                <el-select v-model="field.field_type" @change="handleTypeChange(field)">
                  <el-option
                    v-for="option in fieldTypeOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
              <el-form-item class="field-editor-description" label="填写说明">
                <el-input v-model="field.description" maxlength="500" />
              </el-form-item>
              <el-form-item v-if="usesOptions(field.field_type)" label="可选项" required>
                <el-select
                  v-model="field.options"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="输入选项后按回车"
                />
              </el-form-item>
            </div>
            <div class="field-editor-switches">
              <el-switch v-model="field.enabled" active-text="启用" inactive-text="停用" />
              <el-switch v-model="field.required" active-text="必填" inactive-text="选填" />
              <el-switch
                v-model="field.show_in_export"
                active-text="导出显示"
                inactive-text="导出隐藏"
              />
            </div>
          </article>
        </div>
      </section>

      <aside class="history-card">
        <div class="section-heading">
          <div>
            <span>不可变记录</span>
            <h2>版本历史</h2>
          </div>
        </div>
        <ol class="version-list">
          <li v-for="version in versions" :key="version.id">
            <strong>v{{ version.version_no }}</strong>
            <time>{{ formatShanghaiTime(version.created_at) }}</time>
          </li>
        </ol>
      </aside>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type {
  DailyFieldValue,
  ProjectListEntry,
  ProjectTaskStatus
} from '@renderer/types/daily-report'
import type { TemplateFieldData } from '@renderer/types/template'
import { isProjectListArray, projectTaskStatusLabel } from '@renderer/utils/template-fields'

const props = defineProps<{
  field: TemplateFieldData
  modelValue: DailyFieldValue
  disabled?: boolean
  error?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DailyFieldValue]
}>()

const PROJECT_TASK_STATUSES: ProjectTaskStatus[] = ['TODO', 'DOING', 'DONE']

const textValue = computed(() => (typeof props.modelValue === 'string' ? props.modelValue : ''))
const numberValue = computed(() =>
  typeof props.modelValue === 'number' ? props.modelValue : undefined
)
const multipleValue = computed(() =>
  Array.isArray(props.modelValue) && !isProjectListArray(props.modelValue) ? props.modelValue : []
)
const projectListValue = computed<ProjectListEntry[]>(() =>
  Array.isArray(props.modelValue) && isProjectListArray(props.modelValue) ? props.modelValue : []
)

function updateText(value: unknown): void {
  emit('update:modelValue', typeof value === 'string' ? value : '')
}

function updateNumber(value: unknown): void {
  emit('update:modelValue', typeof value === 'number' ? value : null)
}

function updateMultiple(value: unknown): void {
  emit(
    'update:modelValue',
    Array.isArray(value) && value.every((item) => typeof item === 'string') ? value : []
  )
}

function addProjectListItem(): void {
  emit('update:modelValue', [
    ...projectListValue.value,
    { project: '', content: '', status: 'TODO' }
  ])
}

function removeProjectListItem(index: number): void {
  emit(
    'update:modelValue',
    projectListValue.value.filter((_item, itemIndex) => itemIndex !== index)
  )
}

function updateProjectListItem(index: number, patch: Partial<ProjectListEntry>): void {
  emit(
    'update:modelValue',
    projectListValue.value.map((item, itemIndex) =>
      itemIndex === index ? { ...item, ...patch } : item
    )
  )
}

function updateProjectListProject(index: number, value: unknown): void {
  updateProjectListItem(index, { project: typeof value === 'string' ? value : '' })
}

function updateProjectListContent(index: number, value: unknown): void {
  updateProjectListItem(index, { content: typeof value === 'string' ? value : '' })
}

function updateProjectListStatus(index: number, value: unknown): void {
  const status = PROJECT_TASK_STATUSES.find((candidate) => candidate === value)
  updateProjectListItem(index, { status: status ?? 'TODO' })
}
</script>

<template>
  <el-form-item :label="field.label" :required="field.required" :error="error">
    <el-input
      v-if="field.field_type === 'text'"
      :model-value="textValue"
      :disabled="disabled"
      @update:model-value="updateText"
    />
    <el-input
      v-else-if="field.field_type === 'textarea'"
      :model-value="textValue"
      :disabled="disabled"
      type="textarea"
      :autosize="{ minRows: 4, maxRows: 12 }"
      @update:model-value="updateText"
    />
    <el-input-number
      v-else-if="field.field_type === 'number'"
      :model-value="numberValue"
      :disabled="disabled"
      controls-position="right"
      @update:model-value="updateNumber"
    />
    <el-date-picker
      v-else-if="field.field_type === 'date'"
      :model-value="textValue"
      :disabled="disabled"
      type="date"
      value-format="YYYY-MM-DD"
      format="YYYY-MM-DD"
      @update:model-value="updateText"
    />
    <el-select
      v-else-if="field.field_type === 'select'"
      :model-value="textValue"
      :disabled="disabled"
      clearable
      @update:model-value="updateText"
    >
      <el-option v-for="option in field.options" :key="option" :label="option" :value="option" />
    </el-select>
    <el-select
      v-else-if="field.field_type === 'multiselect'"
      :model-value="multipleValue"
      :disabled="disabled"
      multiple
      clearable
      @update:model-value="updateMultiple"
    >
      <el-option v-for="option in field.options" :key="option" :label="option" :value="option" />
    </el-select>
    <div v-else-if="field.field_type === 'PROJECT_LIST'" class="project-list-field">
      <el-empty v-if="projectListValue.length === 0" description="暂无项目" :image-size="48" />
      <article v-for="(item, index) in projectListValue" :key="index" class="project-list-item">
        <el-input
          :model-value="item.project"
          placeholder="项目名称"
          :disabled="disabled"
          @update:model-value="(value) => updateProjectListProject(index, value)"
        />
        <el-input
          :model-value="item.content"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="工作内容"
          :disabled="disabled"
          @update:model-value="(value) => updateProjectListContent(index, value)"
        />
        <el-select
          :model-value="item.status"
          :disabled="disabled"
          @update:model-value="(value) => updateProjectListStatus(index, value)"
        >
          <el-option
            v-for="status in PROJECT_TASK_STATUSES"
            :key="status"
            :label="projectTaskStatusLabel(status)"
            :value="status"
          />
        </el-select>
        <el-button
          v-if="!disabled"
          link
          type="danger"
          class="project-list-item-remove"
          @click="removeProjectListItem(index)"
        >
          删除
        </el-button>
      </article>
      <el-button v-if="!disabled" @click="addProjectListItem">+ 添加项目</el-button>
    </div>
    <span v-if="field.description" class="field-hint">{{ field.description }}</span>
  </el-form-item>
</template>

<style scoped>
.project-list-field {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.project-list-item {
  display: grid;
  grid-template-columns: 1fr 2fr auto auto;
  align-items: start;
  gap: 8px;
}

.project-list-item-remove {
  align-self: center;
}
</style>

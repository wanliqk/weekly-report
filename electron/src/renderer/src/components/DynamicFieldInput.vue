<script setup lang="ts">
import { computed } from 'vue'

import type { DailyFieldValue, ProjectListEntry } from '@renderer/types/daily-report'
import type { TemplateFieldData } from '@renderer/types/template'
import { emptyProjectListEntry, isProjectListArray } from '@renderer/utils/template-fields'

const props = withDefaults(
  defineProps<{
    field: TemplateFieldData
    modelValue: DailyFieldValue
    defaultOwner?: string
    disabled?: boolean
    error?: string
  }>(),
  {
    defaultOwner: ''
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: DailyFieldValue]
}>()

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
  emit('update:modelValue', [...projectListValue.value, emptyProjectListEntry(props.defaultOwner)])
}

function removeProjectListItem(index: number): void {
  emit(
    'update:modelValue',
    projectListValue.value.filter((_item, itemIndex) => itemIndex !== index)
  )
}

function updateProjectListField(
  index: number,
  field: keyof ProjectListEntry,
  value: unknown
): void {
  emit(
    'update:modelValue',
    projectListValue.value.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: typeof value === 'string' ? value : '' } : item
    )
  )
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
        <div class="project-list-item-row project-list-item-row--two">
          <el-input
            :model-value="item.category"
            placeholder="类别"
            :disabled="disabled"
            @update:model-value="(value) => updateProjectListField(index, 'category', value)"
          />
          <el-input
            :model-value="item.project"
            placeholder="工作项目"
            :disabled="disabled"
            @update:model-value="(value) => updateProjectListField(index, 'project', value)"
          />
        </div>
        <el-input
          :model-value="item.content"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="工作步骤"
          :disabled="disabled"
          @update:model-value="(value) => updateProjectListField(index, 'content', value)"
        />
        <div class="project-list-item-row">
          <el-input
            :model-value="item.weight"
            placeholder="权重"
            :disabled="disabled"
            @update:model-value="(value) => updateProjectListField(index, 'weight', value)"
          />
          <el-input
            :model-value="item.planned_completion_date"
            placeholder="预计完成时间节点"
            :disabled="disabled"
            @update:model-value="
              (value) => updateProjectListField(index, 'planned_completion_date', value)
            "
          />
          <el-input
            :model-value="item.actual_completion_date"
            placeholder="实际完成时间"
            :disabled="disabled"
            @update:model-value="
              (value) => updateProjectListField(index, 'actual_completion_date', value)
            "
          />
        </div>
        <div class="project-list-item-row">
          <el-input
            :model-value="item.owner"
            placeholder="责任人"
            :disabled="disabled"
            @update:model-value="(value) => updateProjectListField(index, 'owner', value)"
          />
          <el-input
            :model-value="item.assistant"
            placeholder="协助人"
            :disabled="disabled"
            @update:model-value="(value) => updateProjectListField(index, 'assistant', value)"
          />
          <el-input
            :model-value="item.required_resources"
            placeholder="所需资源支持"
            :disabled="disabled"
            @update:model-value="
              (value) => updateProjectListField(index, 'required_resources', value)
            "
          />
        </div>
        <el-input
          :model-value="item.completion_notes"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="实际完成情况及解决措施"
          :disabled="disabled"
          @update:model-value="(value) => updateProjectListField(index, 'completion_notes', value)"
        />
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
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.project-list-item-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.project-list-item-row--two {
  grid-template-columns: repeat(2, 1fr);
}

.project-list-item-remove {
  align-self: flex-end;
}
</style>

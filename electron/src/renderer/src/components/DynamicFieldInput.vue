<script setup lang="ts">
import { computed } from 'vue'

import type { DailyFieldValue } from '@renderer/types/daily-report'
import type { TemplateFieldData } from '@renderer/types/template'

const props = defineProps<{
  field: TemplateFieldData
  modelValue: DailyFieldValue
  disabled?: boolean
  error?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: DailyFieldValue]
}>()

const textValue = computed(() => (typeof props.modelValue === 'string' ? props.modelValue : ''))
const numberValue = computed(() =>
  typeof props.modelValue === 'number' ? props.modelValue : undefined
)
const multipleValue = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []))

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
      v-else
      :model-value="multipleValue"
      :disabled="disabled"
      multiple
      clearable
      @update:model-value="updateMultiple"
    >
      <el-option v-for="option in field.options" :key="option" :label="option" :value="option" />
    </el-select>
    <span v-if="field.description" class="field-hint">{{ field.description }}</span>
  </el-form-item>
</template>

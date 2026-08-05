export type TemplateFieldType = 'text' | 'textarea' | 'number' | 'date' | 'select' | 'multiselect'

export type TemplateCoreType = 'today_work' | 'tomorrow_plan'

export interface TemplateFieldData {
  field_key: string
  label: string
  description: string
  field_type: TemplateFieldType
  required: boolean
  enabled: boolean
  sort_order: number
  options: string[]
  core_type: TemplateCoreType | null
}

export interface TemplateFieldInput {
  field_key?: string
  label: string
  description: string
  field_type: TemplateFieldType
  required: boolean
  enabled: boolean
  sort_order: number
  options: string[]
}

export interface TemplateData {
  id: string
  name: string
  version_no: number
  fields: TemplateFieldData[]
}

export interface TemplateVersionSummaryData {
  id: string
  version_no: number
  created_at: string
}

export interface TemplateVersionsData {
  items: TemplateVersionSummaryData[]
}

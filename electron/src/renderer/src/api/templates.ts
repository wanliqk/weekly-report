import { requestData } from './client'
import type { TemplateData, TemplateFieldInput, TemplateVersionsData } from '../types/template'

export function getCurrentTemplate(): Promise<TemplateData> {
  return requestData({ method: 'GET', url: '/api/v1/report-templates/current' })
}

export function publishTemplate(fields: TemplateFieldInput[]): Promise<TemplateData> {
  return requestData({
    method: 'PUT',
    url: '/api/v1/report-templates/current',
    data: { fields }
  })
}

export function listTemplateVersions(): Promise<TemplateVersionsData> {
  return requestData({ method: 'GET', url: '/api/v1/report-templates/versions' })
}

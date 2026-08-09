import { requestData } from './client'
import type {
  WeComConnectionData,
  WeComPreviewData,
  WeComProfileData,
  WeComProfileUpdateRequest,
  WeComSyncRecordCreateData,
  WeComSyncRecordData,
  WeComSyncRecordListData,
  WeComSyncRecordQuery
} from '../types/wecom'

export function getWeComConnection(): Promise<WeComConnectionData> {
  return requestData({ method: 'GET', url: '/api/v1/wecom/connection' })
}

export function getWeComProfile(): Promise<WeComProfileData> {
  return requestData({ method: 'GET', url: '/api/v1/wecom/profile' })
}

export function updateWeComProfile(payload: WeComProfileUpdateRequest): Promise<WeComProfileData> {
  return requestData({ method: 'PUT', url: '/api/v1/wecom/profile', data: payload })
}

export function createWeComPreview(dailyReportDayId: string): Promise<WeComPreviewData> {
  return requestData({
    method: 'POST',
    url: '/api/v1/wecom/previews',
    data: { daily_report_day_id: dailyReportDayId }
  })
}

export function createOrGetWeComDaySync(workDate: string): Promise<WeComSyncRecordCreateData> {
  return requestData({
    method: 'POST',
    url: `/api/v1/daily-report-days/${workDate}/wecom-syncs`
  })
}

export function listWeComSyncRecords(
  query: WeComSyncRecordQuery = {}
): Promise<WeComSyncRecordListData> {
  return requestData({ method: 'GET', url: '/api/v1/wecom/sync-records', params: query })
}

export function getWeComSyncRecord(recordId: string): Promise<WeComSyncRecordData> {
  return requestData({ method: 'GET', url: `/api/v1/wecom/sync-records/${recordId}` })
}

export function retryWeComSyncRecord(recordId: string): Promise<WeComSyncRecordData> {
  return requestData({ method: 'POST', url: `/api/v1/wecom/sync-records/${recordId}/retry` })
}

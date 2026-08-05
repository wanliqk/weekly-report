import { requestData } from './client'
import type { CapabilitiesData, SettingsData } from '../types/settings'

export function getMySettings(): Promise<SettingsData> {
  return requestData({ method: 'GET', url: '/api/v1/settings/me' })
}

export function updateMySettings(autoArchiveOnSubmit: boolean): Promise<SettingsData> {
  return requestData({
    method: 'PATCH',
    url: '/api/v1/settings/me',
    data: { auto_archive_on_submit: autoArchiveOnSubmit }
  })
}

export function getCapabilities(): Promise<CapabilitiesData> {
  return requestData({ method: 'GET', url: '/api/v1/capabilities' })
}

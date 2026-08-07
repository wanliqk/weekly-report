import { requestData } from './client'
import type { CapabilitiesData, SettingsData } from '../types/settings'

export function getMySettings(): Promise<SettingsData> {
  return requestData({ method: 'GET', url: '/api/v1/settings/me' })
}

export function getCapabilities(): Promise<CapabilitiesData> {
  return requestData({ method: 'GET', url: '/api/v1/capabilities' })
}

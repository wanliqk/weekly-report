import { requestData } from './client'
import type { UserData } from '../types/user'

export interface BootstrapStatusData {
  initialized: boolean
}

export interface LoginData {
  access_token: string
  expires_at: string
}

export function getBootstrapStatus(): Promise<BootstrapStatusData> {
  return requestData({ method: 'GET', url: '/api/v1/system/bootstrap-status' })
}

export function bootstrapAdmin(payload: {
  username: string
  password: string
  display_name: string
}): Promise<UserData> {
  return requestData({ method: 'POST', url: '/api/v1/system/bootstrap-admin', data: payload })
}

export function login(payload: { username: string; password: string }): Promise<LoginData> {
  return requestData({ method: 'POST', url: '/api/v1/auth/login', data: payload })
}

export function getMe(): Promise<UserData> {
  return requestData({ method: 'GET', url: '/api/v1/auth/me' })
}

export function changePassword(payload: {
  current_password: string
  new_password: string
}): Promise<Record<string, never>> {
  return requestData({ method: 'PUT', url: '/api/v1/auth/password', data: payload })
}

export function logout(): Promise<Record<string, never>> {
  return requestData({ method: 'POST', url: '/api/v1/auth/logout' })
}

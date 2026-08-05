import { requestData } from './client'
import type { UserData, UserListData, UserRole } from '../types/user'

export function listUsers(page = 1, pageSize = 20): Promise<UserListData> {
  return requestData({
    method: 'GET',
    url: '/api/v1/users',
    params: { page, page_size: pageSize }
  })
}

export function createUser(payload: {
  username: string
  password: string
  display_name: string
  role: UserRole
}): Promise<UserData> {
  return requestData({ method: 'POST', url: '/api/v1/users', data: payload })
}

export function updateUser(
  userId: string,
  payload: { display_name?: string; role?: UserRole; is_active?: boolean }
): Promise<UserData> {
  return requestData({ method: 'PATCH', url: `/api/v1/users/${userId}`, data: payload })
}

export function resetUserPassword(userId: string, newPassword: string): Promise<UserData> {
  return requestData({
    method: 'PUT',
    url: `/api/v1/users/${userId}/password`,
    data: { new_password: newPassword }
  })
}

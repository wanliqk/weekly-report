export type UserRole = 'admin' | 'user'
export type CannotDeleteReason = 'self' | 'last_active_admin' | 'has_business_records'

export interface UserData {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  can_delete: boolean
  cannot_delete_reason: CannotDeleteReason | null
}

export interface UserListData {
  items: UserData[]
  page: number
  page_size: number
  total: number
}

export interface MeData extends UserData {
  must_change_password: boolean
}

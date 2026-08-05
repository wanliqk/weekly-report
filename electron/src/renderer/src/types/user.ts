export type UserRole = 'admin' | 'user'

export interface UserData {
  id: string
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserListData {
  items: UserData[]
  page: number
  page_size: number
  total: number
}

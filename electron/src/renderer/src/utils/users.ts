import type { CannotDeleteReason } from '../types/user'

export function cannotDeleteReasonLabel(reason: CannotDeleteReason | null): string | null {
  if (reason === null) {
    return null
  }
  return {
    self: '不能删除当前登录账号',
    last_active_admin: '不能删除最后一个有效管理员',
    has_business_records: '已有业务记录，请停用账号'
  }[reason]
}

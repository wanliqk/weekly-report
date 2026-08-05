// 服务端统一响应协议类型（ai-docs/api.md §2、ADR-006）。
// 所有接口信封为 {code, msg, data}；分页为 {items, page, page_size, total}。
// 字段保持 snake_case，与后端契约一致；业务页面如需 camelCase 在 api 适配层转换。

export interface ApiEnvelope<T = unknown> {
  code: number
  msg: string
  data: T
}

export interface PageResult<T> {
  items: T[]
  page: number
  page_size: number
  total: number
}

export interface ApiFieldError {
  field: string
  message: string
}

export function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    'msg' in value &&
    'data' in value
  )
}

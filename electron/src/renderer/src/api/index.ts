// HTTP 唯一入口（架构 §3.2）：页面与组件一律从本模块导入，
// 禁止直接使用 axios。业务 API 模块（api/modules/*）在对应任务中补充。

export { apiClient, setAccessToken, registerUnauthorizedHandler } from './client'
export { ApiError, ApiErrorCode, parseApiError, toUserMessage } from './errors'
export type { ApiErrorCodeValue } from './errors'
export { confirmAction, notifyError, notifyInfo, notifySuccess, notifyWarning } from './feedback'
export { isApiEnvelope } from '../types/api'
export type { ApiEnvelope, ApiFieldError, PageResult } from '../types/api'

import { AxiosError } from 'axios'
import { isApiEnvelope } from '../types/api'

// 业务错误码（ai-docs/api.md §3），数值与后端契约保持一致，不得随意变更。
export const ApiErrorCode = {
  PARAM_INVALID: 40001,
  INVALID_CREDENTIALS: 40101,
  TOKEN_INVALID: 40102,
  ROLE_FORBIDDEN: 40301,
  OWNERSHIP_FORBIDDEN: 40302,
  NOT_FOUND: 40401,
  DAILY_REPORT_EXISTS: 40901,
  ILLEGAL_TRANSITION: 40902,
  WEEKLY_REPORT_EXISTS: 40903,
  VERSION_CONFLICT: 40904,
  FIELD_VALIDATION: 42201,
  INTERNAL_ERROR: 50001,
  UNAVAILABLE: 50301
} as const

export type ApiErrorCodeValue = (typeof ApiErrorCode)[keyof typeof ApiErrorCode]

// 统一前端错误对象：携带稳定业务 code、HTTP 状态与响应 data，
// 页面只处理 ApiError，不直接接触 Axios 原始错误。
export class ApiError extends Error {
  readonly code: number
  readonly httpStatus: number
  readonly data: unknown

  constructor(code: number, message: string, data?: unknown, httpStatus = 0) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.data = data
    this.httpStatus = httpStatus
  }
}

export function toUserMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return '发生未知错误，请稍后重试'
}

export function parseApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? 0
    const body = error.response?.data
    if (isApiEnvelope(body)) {
      return new ApiError(body.code, body.msg, body.data, status)
    }
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return new ApiError(ApiErrorCode.UNAVAILABLE, '请求超时，请稍后重试', undefined, status)
    }
    if (!error.response) {
      return new ApiError(ApiErrorCode.UNAVAILABLE, '无法连接本地服务，请稍后重试', undefined, 0)
    }
    return new ApiError(ApiErrorCode.INTERNAL_ERROR, '请求失败，请稍后重试', undefined, status)
  }
  return new ApiError(ApiErrorCode.INTERNAL_ERROR, '发生未知错误，请稍后重试', undefined, 0)
}

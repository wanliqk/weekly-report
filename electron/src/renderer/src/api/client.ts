import axios, { AxiosError } from 'axios'
import { getActivePinia } from 'pinia'
import { isApiEnvelope } from '../types/api'
import type { RendererBridge, WindowWithBridge } from '../types/bridge'
import { useUiStore } from '../stores/ui'
import { ApiError, ApiErrorCode, parseApiError, toUserMessage } from './errors'
import { notifyError } from './feedback'

declare module 'axios' {
  export interface AxiosRequestConfig {
    // 请求级静默标记：置 true 时拦截器不自动弹出全局错误提示，
    // 由调用方自行处理错误反馈（如表单内联错误）。
    silent?: boolean
  }
}

// 运行期桥接：API 基址与请求头（X-Runtime-Secret 等）由 DESK-03 通过
// contextBridge 提供，FE-01 仅做防御性读取，不依赖当前 preload 实现。
function getRendererBridge(): RendererBridge | undefined {
  const win = window as WindowWithBridge
  return win.api
}

function beginGlobalLoading(): void {
  const pinia = getActivePinia()
  if (pinia) {
    useUiStore().beginRequest()
  }
}

function endGlobalLoading(): void {
  const pinia = getActivePinia()
  if (pinia) {
    useUiStore().endRequest()
  }
}

// 运行期 Token 由 FE-AUTH-01 注入；40102 处理钩子同样由认证任务注册。
// 本文件只承载机制，不承载认证业务。
let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

let unauthorizedHandler: (error: ApiError) => void = () => {}

export function registerUnauthorizedHandler(handler: (error: ApiError) => void): void {
  unauthorizedHandler = handler
}

// HTTP 唯一入口：页面与组件禁止直接使用 axios，一律经由本 client 或 api 模块。
export const apiClient = axios.create({
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' }
})

apiClient.interceptors.request.use((config) => {
  const bridge = getRendererBridge()
  if (!config.baseURL && bridge?.apiBaseUrl) {
    config.baseURL = bridge.apiBaseUrl
  }
  if (bridge?.runtimeHeaders) {
    for (const [key, value] of Object.entries(bridge.runtimeHeaders)) {
      config.headers.set(key, value)
    }
  }
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }
  beginGlobalLoading()
  return config
})

apiClient.interceptors.response.use(
  (response) => {
    endGlobalLoading()
    const body = response.data
    if (isApiEnvelope(body) && body.code !== 0) {
      const error = new ApiError(body.code, body.msg, body.data, response.status)
      if (!response.config.silent) {
        notifyError(toUserMessage(error))
      }
      return Promise.reject(error)
    }
    return response
  },
  (error: unknown) => {
    endGlobalLoading()
    const apiError = parseApiError(error)
    const silent = error instanceof AxiosError ? error.config?.silent === true : false
    if (!silent) {
      notifyError(toUserMessage(apiError))
    }
    if (apiError.code === ApiErrorCode.TOKEN_INVALID) {
      unauthorizedHandler(apiError)
    }
    return Promise.reject(apiError)
  }
)

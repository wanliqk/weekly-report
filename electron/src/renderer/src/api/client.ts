import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'

interface ApiEnvelope<DataT> {
  code: number
  msg: string
  data: DataT
}

interface AuthClientHooks {
  getAccessToken: () => string | null
  onTokenInvalid: () => void | Promise<void>
  onPasswordChangeRequired: () => void | Promise<void>
}

let cachedClient: Promise<AxiosInstance> | null = null
let authHooks: AuthClientHooks = {
  getAccessToken: () => null,
  onTokenInvalid: () => undefined,
  onPasswordChangeRequired: () => undefined
}

export class ApiError extends Error {
  constructor(
    readonly code: number,
    message: string,
    readonly status: number | null,
    readonly data: unknown = {}
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function configureApiAuth(hooks: AuthClientHooks): void {
  authHooks = hooks
}

export async function requestData<DataT>(request: AxiosRequestConfig): Promise<DataT> {
  try {
    const client = await getApiClient()
    const response = await client.request<ApiEnvelope<DataT>>(request)
    if (response.data.code !== 0) {
      throw new ApiError(response.data.code, response.data.msg, response.status, response.data.data)
    }
    return response.data.data
  } catch (error) {
    const apiError = normalizeApiError(error)
    await handleAuthErrorCodes(apiError)
    throw apiError
  }
}

export interface BinaryResponse {
  data: ArrayBuffer
  fileName: string | null
}

export async function requestBinary(request: AxiosRequestConfig): Promise<BinaryResponse> {
  try {
    const client = await getApiClient()
    const response = await client.request<ArrayBuffer>({
      ...request,
      responseType: 'arraybuffer'
    })
    return {
      data: response.data,
      fileName: extractFileName(response.headers['content-disposition'])
    }
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.data instanceof ArrayBuffer) {
      error.response.data = decodeArrayBufferErrorBody(error.response.data)
    }
    const apiError = normalizeApiError(error)
    await handleAuthErrorCodes(apiError)
    throw apiError
  }
}

async function handleAuthErrorCodes(error: ApiError): Promise<void> {
  if (error.code === 40102) {
    await authHooks.onTokenInvalid()
  } else if (error.code === 40303) {
    await authHooks.onPasswordChangeRequired()
  }
}

export function userMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return '操作失败，请稍后重试'
}

export function resetApiClient(): void {
  cachedClient = null
}

async function getApiClient(): Promise<AxiosInstance> {
  cachedClient ??= createClient()
  return cachedClient
}

async function createClient(): Promise<AxiosInstance> {
  const config = await window.runtimeBridge.api.getConfig()
  if (!config) {
    throw new ApiError(50301, '本地服务尚未就绪', 503)
  }
  const client = axios.create({
    baseURL: config.baseUrl,
    headers: {
      [config.runtimeSecretHeader]: config.runtimeSecret
    }
  })
  client.interceptors.request.use((request) => {
    const token = authHooks.getAccessToken()
    if (token) {
      request.headers.Authorization = `Bearer ${token}`
    } else {
      delete request.headers.Authorization
    }
    return request
  })
  return client
}

function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (axios.isAxiosError(error)) {
    const body = error.response?.data
    if (isApiEnvelope(body)) {
      return new ApiError(body.code, body.msg, error.response?.status ?? null, body.data)
    }
    return new ApiError(50001, '无法连接本地服务，请稍后重试', error.response?.status ?? null)
  }
  return new ApiError(50001, userMessage(error), null)
}

function extractFileName(headerValue: unknown): string | null {
  if (typeof headerValue !== 'string') {
    return null
  }
  const encodedMatch = /filename\*=UTF-8''([^;]+)/i.exec(headerValue)
  if (encodedMatch) {
    try {
      return decodeURIComponent(encodedMatch[1])
    } catch {
      // fall through to the plain `filename=` parameter below
    }
  }
  const match = /filename="([^"]+)"/.exec(headerValue)
  return match ? match[1] : null
}

// The backend always returns the unified `{code,msg,data}` envelope, even
// for error responses on a binary download route — but with
// `responseType: 'arraybuffer'` axios hands the error body back as raw
// bytes instead of parsed JSON, so `normalizeApiError` would otherwise miss
// the real business code (e.g. 40401) and fall back to a generic message.
function decodeArrayBufferErrorBody(data: ArrayBuffer): unknown {
  try {
    return JSON.parse(new TextDecoder().decode(data))
  } catch {
    return data
  }
}

function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    typeof value.code === 'number' &&
    'msg' in value &&
    typeof value.msg === 'string' &&
    'data' in value
  )
}

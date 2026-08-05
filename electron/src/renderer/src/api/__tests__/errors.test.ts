import { AxiosError, AxiosHeaders } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { describe, expect, it } from 'vitest'
import { ApiError, ApiErrorCode, parseApiError } from '../errors'

function createAxiosError(status: number, data: unknown, code?: string): AxiosError {
  const config: InternalAxiosRequestConfig = {
    headers: new AxiosHeaders(),
    method: 'get',
    url: '/api/v1/test'
  }
  const response: AxiosResponse = {
    data,
    status,
    statusText: 'Error',
    headers: {},
    config
  }
  return new AxiosError(
    'Request failed',
    code ?? AxiosError.ERR_BAD_RESPONSE,
    config,
    null,
    response
  )
}

describe('parseApiError 错误映射', () => {
  it('透传已构造的 ApiError', () => {
    const original = new ApiError(
      ApiErrorCode.VERSION_CONFLICT,
      '数据已被修改',
      { version: 3 },
      409
    )
    expect(parseApiError(original)).toBe(original)
  })

  it('将带统一信封的 Axios 错误映射为 ApiError', () => {
    const error = createAxiosError(409, {
      code: 40904,
      msg: '乐观锁版本冲突',
      data: { version: 5 }
    })
    const mapped = parseApiError(error)
    expect(mapped).toBeInstanceOf(ApiError)
    expect(mapped.code).toBe(40904)
    expect(mapped.message).toBe('乐观锁版本冲突')
    expect(mapped.httpStatus).toBe(409)
    expect(mapped.data).toEqual({ version: 5 })
  })

  it('将超时错误映射为服务不可用', () => {
    const error = createAxiosError(0, undefined, AxiosError.ECONNABORTED)
    const mapped = parseApiError(error)
    expect(mapped.code).toBe(ApiErrorCode.UNAVAILABLE)
    expect(mapped.message).toBe('请求超时，请稍后重试')
  })

  it('将无响应错误（本地服务不可达）映射为服务不可用', () => {
    const error = new AxiosError('Network Error', AxiosError.ERR_NETWORK, {
      headers: new AxiosHeaders(),
      method: 'get',
      url: '/api/v1/test'
    })
    const mapped = parseApiError(error)
    expect(mapped.code).toBe(ApiErrorCode.UNAVAILABLE)
    expect(mapped.httpStatus).toBe(0)
  })

  it('将非信封响应映射为内部错误', () => {
    const error = createAxiosError(500, '<html>oops</html>')
    const mapped = parseApiError(error)
    expect(mapped.code).toBe(ApiErrorCode.INTERNAL_ERROR)
    expect(mapped.httpStatus).toBe(500)
  })

  it('将未知错误映射为内部错误', () => {
    const mapped = parseApiError('boom')
    expect(mapped.code).toBe(ApiErrorCode.INTERNAL_ERROR)
    expect(mapped.message).toBe('发生未知错误，请稍后重试')
  })
})

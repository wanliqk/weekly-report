import { request } from 'node:http'

import {
  HEALTH_POLL_INTERVAL_MS,
  HEALTH_POLL_TIMEOUT_MS,
  HEALTH_REQUEST_TIMEOUT_MS
} from './constants'

export class HealthCheckTimeoutError extends Error {
  constructor() {
    super('sidecar health check timed out')
    this.name = 'HealthCheckTimeoutError'
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function checkOnce(baseUrl: string): Promise<boolean> {
  return new Promise((resolve) => {
    const req = request(
      `${baseUrl}/health`,
      { method: 'GET', timeout: HEALTH_REQUEST_TIMEOUT_MS },
      (res) => {
        res.resume()
        resolve(res.statusCode === 200)
      }
    )
    req.on('timeout', () => req.destroy())
    req.on('error', () => resolve(false))
    req.end()
  })
}

export interface WaitForHealthyOptions {
  pollIntervalMs?: number
  timeoutMs?: number
  /** Polled between attempts; return true to bail out early (e.g. the child process already exited). */
  isAborted?: () => boolean
}

export async function waitForHealthy(
  baseUrl: string,
  options: WaitForHealthyOptions = {}
): Promise<void> {
  const pollIntervalMs = options.pollIntervalMs ?? HEALTH_POLL_INTERVAL_MS
  const timeoutMs = options.timeoutMs ?? HEALTH_POLL_TIMEOUT_MS
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    if (options.isAborted?.()) {
      throw new HealthCheckTimeoutError()
    }
    if (await checkOnce(baseUrl)) {
      return
    }
    await sleep(pollIntervalMs)
  }

  throw new HealthCheckTimeoutError()
}

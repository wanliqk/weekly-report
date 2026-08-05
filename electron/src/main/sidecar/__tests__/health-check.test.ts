import { createServer, type Server } from 'node:http'

import { afterEach, describe, expect, it } from 'vitest'

import { HealthCheckTimeoutError, waitForHealthy } from '../health-check'

function listenOnEphemeralPort(server: Server): Promise<number> {
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      if (address === null || typeof address === 'string') {
        throw new Error('expected a network address')
      }
      resolve(address.port)
    })
  })
}

function closeServer(server: Server): Promise<void> {
  return new Promise((resolve) => server.close(() => resolve()))
}

describe('waitForHealthy', () => {
  let server: Server | null = null

  afterEach(async () => {
    if (server) {
      await closeServer(server)
      server = null
    }
  })

  it('resolves once the endpoint answers with 200', async () => {
    server = createServer((_req, res) => {
      res.writeHead(200)
      res.end()
    })
    const port = await listenOnEphemeralPort(server)

    await expect(
      waitForHealthy(`http://127.0.0.1:${port}`, { pollIntervalMs: 10, timeoutMs: 2000 })
    ).resolves.toBeUndefined()
  })

  it('keeps polling through non-200 responses until one succeeds', async () => {
    let requestCount = 0
    server = createServer((_req, res) => {
      requestCount += 1
      res.writeHead(requestCount < 3 ? 503 : 200)
      res.end()
    })
    const port = await listenOnEphemeralPort(server)

    await waitForHealthy(`http://127.0.0.1:${port}`, { pollIntervalMs: 10, timeoutMs: 2000 })

    expect(requestCount).toBeGreaterThanOrEqual(3)
  })

  it('rejects with HealthCheckTimeoutError when nothing answers in time', async () => {
    await expect(
      waitForHealthy('http://127.0.0.1:1', { pollIntervalMs: 10, timeoutMs: 50 })
    ).rejects.toBeInstanceOf(HealthCheckTimeoutError)
  })

  it('aborts early when isAborted() reports true', async () => {
    await expect(
      waitForHealthy('http://127.0.0.1:1', {
        pollIntervalMs: 10,
        timeoutMs: 5000,
        isAborted: () => true
      })
    ).rejects.toBeInstanceOf(HealthCheckTimeoutError)
  })
})

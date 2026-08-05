import { mkdtemp, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import {
  type SafeStorageAdapter,
  SecureTokenStore,
  SecureTokenStoreError
} from '../secure-token-store'

const directories: string[] = []

async function tokenPath(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), 'weekly-report-token-'))
  directories.push(directory)
  return join(directory, 'access-token.bin')
}

function adapter(available = true): SafeStorageAdapter {
  return {
    isEncryptionAvailable: () => available,
    encryptString: (plainText: string) => Buffer.from(plainText).reverse(),
    decryptString: (encrypted: Buffer) => encrypted.reverse().toString('utf8')
  }
}

afterEach(async () => {
  const { rm } = await import('node:fs/promises')
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })))
})

describe('SecureTokenStore', () => {
  it('stores only encrypted bytes and restores the token', async () => {
    const path = await tokenPath()
    const store = new SecureTokenStore(path, adapter())

    await store.setToken('header.payload.signature')

    expect((await readFile(path, 'utf8')).includes('header.payload.signature')).toBe(false)
    expect(await store.getToken()).toEqual({
      available: true,
      token: 'header.payload.signature',
      reason: null
    })
  })

  it('clears a saved token idempotently', async () => {
    const path = await tokenPath()
    const store = new SecureTokenStore(path, adapter())
    await store.setToken('header.payload.signature')

    await store.clearToken()
    await store.clearToken()

    expect(await store.getToken()).toEqual({ available: true, token: null, reason: null })
  })

  it('reports unavailable encryption without writing plaintext fallback', async () => {
    const path = await tokenPath()
    const store = new SecureTokenStore(path, adapter(false))

    const result = await store.setToken('header.payload.signature')

    expect(result).toEqual({
      available: false,
      token: null,
      reason: 'secure-storage-unavailable'
    })
    await expect(readFile(path)).rejects.toMatchObject({ code: 'ENOENT' })
  })

  it('rejects empty or unreasonably large token payloads', async () => {
    const path = await tokenPath()
    const store = new SecureTokenStore(path, adapter())

    await expect(store.setToken('')).rejects.toBeInstanceOf(SecureTokenStoreError)
    await expect(store.setToken('x'.repeat(16_385))).rejects.toBeInstanceOf(SecureTokenStoreError)
  })
})

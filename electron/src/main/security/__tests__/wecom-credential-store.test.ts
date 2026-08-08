import { mkdtemp, readdir, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, describe, expect, it } from 'vitest'

import type { SafeStorageAdapter } from '../secure-token-store'
import {
  type WeComCookie,
  WeComCredentialStore,
  WeComCredentialStoreError
} from '../wecom-credential-store'

const directories: string[] = []

async function credentialDir(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), 'weekly-report-wecom-cred-'))
  directories.push(directory)
  return join(directory, 'wecom-credentials')
}

function adapter(available = true): SafeStorageAdapter {
  return {
    isEncryptionAvailable: () => available,
    encryptString: (plainText: string) => Buffer.from(plainText).reverse(),
    decryptString: (encrypted: Buffer) => encrypted.reverse().toString('utf8')
  }
}

function sampleCookieJar(): WeComCookie[] {
  return [
    {
      name: 'wedoc_sid',
      value: 'session-value',
      domain: 'doc.weixin.qq.com',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'lax',
      expirationDate: 1_999_999_999
    },
    {
      name: 'TOK',
      value: 'tok-value',
      domain: 'doc.weixin.qq.com',
      path: '/',
      secure: true,
      httpOnly: false,
      sameSite: 'unspecified',
      expirationDate: null
    }
  ]
}

afterEach(async () => {
  const { rm } = await import('node:fs/promises')
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })))
})

describe('WeComCredentialStore', () => {
  it('saves a cookie jar under a freshly generated slot and restores it', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())
    const jar = sampleCookieJar()

    const slot = await store.save(jar)

    expect(slot).toMatch(/^[0-9a-f]{32}$/)
    const fileContents = await readFile(join(directory, `${slot}.bin`))
    expect(fileContents.toString('utf8')).not.toContain('wedoc_sid')
    expect(fileContents.toString('utf8')).not.toContain('session-value')
    await expect(store.load(slot)).resolves.toEqual(jar)
  })

  it('writes credential files with owner-only permissions', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())

    const slot = await store.save(sampleCookieJar())

    if (process.platform !== 'win32') {
      const { stat } = await import('node:fs/promises')
      const stats = await stat(join(directory, `${slot}.bin`))
      expect(stats.mode & 0o777).toBe(0o600)
    }
  })

  it('keeps multiple slots fully isolated from each other', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())
    const jarA = sampleCookieJar()
    const jarB = [
      {
        ...sampleCookieJar()[0],
        value: 'a-completely-different-session'
      }
    ]

    const slotA = await store.save(jarA)
    const slotB = await store.save(jarB)

    expect(slotA).not.toBe(slotB)
    await expect(store.load(slotA)).resolves.toEqual(jarA)
    await expect(store.load(slotB)).resolves.toEqual(jarB)

    await store.delete(slotA)

    await expect(store.load(slotA)).resolves.toBeNull()
    await expect(store.load(slotB)).resolves.toEqual(jarB)
  })

  it('returns null for a slot that was never created', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())

    await expect(store.load('a'.repeat(32))).resolves.toBeNull()
  })

  it('never falls back to plaintext when encryption is unavailable', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter(false))

    await expect(store.save(sampleCookieJar())).rejects.toBeInstanceOf(WeComCredentialStoreError)
    await expect(readdir(directory).catch(() => [])).resolves.toEqual([])
  })

  it('reports encryption-unavailable as an error when reading, not a silent plaintext read', async () => {
    const directory = await credentialDir()
    const writableStore = new WeComCredentialStore(directory, adapter(true))
    const slot = await writableStore.save(sampleCookieJar())

    const unavailableStore = new WeComCredentialStore(directory, adapter(false))
    await expect(unavailableStore.load(slot)).rejects.toBeInstanceOf(WeComCredentialStoreError)
  })

  it('safely reports a corrupted ciphertext instead of throwing an unhandled exception', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())
    const slot = await store.save(sampleCookieJar())

    // Overwrite with bytes that will decrypt (via the reversing test adapter)
    // to something that is not valid JSON / not a valid cookie jar shape.
    await writeFile(join(directory, `${slot}.bin`), Buffer.from('not-json-and-not-a-jar'))

    await expect(store.load(slot)).rejects.toBeInstanceOf(WeComCredentialStoreError)
  })

  it('deleting a slot that does not exist does not throw', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())

    await expect(store.delete('f'.repeat(32))).resolves.toBeUndefined()
  })

  it('rejects a malformed slot id instead of touching the filesystem', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())

    await expect(store.load('../../etc/passwd')).rejects.toBeInstanceOf(WeComCredentialStoreError)
    await expect(store.delete('not-a-hex-slot')).rejects.toBeInstanceOf(WeComCredentialStoreError)
  })

  it('rejects an empty or malformed cookie jar payload', async () => {
    const directory = await credentialDir()
    const store = new WeComCredentialStore(directory, adapter())

    await expect(store.save([])).rejects.toBeInstanceOf(WeComCredentialStoreError)
    await expect(store.save([{ name: 'x' } as unknown as WeComCookie])).rejects.toBeInstanceOf(
      WeComCredentialStoreError
    )
  })
})

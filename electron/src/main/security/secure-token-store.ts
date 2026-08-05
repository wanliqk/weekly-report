import { readFile, unlink, writeFile } from 'node:fs/promises'

import type { SecureTokenSnapshot } from '../../shared/contracts'

const MAX_TOKEN_LENGTH = 16_384

export interface SafeStorageAdapter {
  isEncryptionAvailable: () => boolean
  encryptString: (plainText: string) => Buffer
  decryptString: (encrypted: Buffer) => string
}

export class SecureTokenStoreError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'SecureTokenStoreError'
  }
}

export class SecureTokenStore {
  constructor(
    private readonly tokenPath: string,
    private readonly safeStorage: SafeStorageAdapter
  ) {}

  async getToken(): Promise<SecureTokenSnapshot> {
    if (!this.safeStorage.isEncryptionAvailable()) {
      return this.unavailableSnapshot()
    }

    let encrypted: Buffer
    try {
      encrypted = await readFile(this.tokenPath)
    } catch (error) {
      if (isFileNotFound(error)) {
        return { available: true, token: null, reason: null }
      }
      throw new SecureTokenStoreError('无法读取安全登录状态')
    }

    try {
      const token = this.safeStorage.decryptString(encrypted)
      validateToken(token)
      return { available: true, token, reason: null }
    } catch {
      throw new SecureTokenStoreError('安全登录状态已损坏，请重新登录')
    }
  }

  async setToken(token: string): Promise<SecureTokenSnapshot> {
    if (!this.safeStorage.isEncryptionAvailable()) {
      return this.unavailableSnapshot()
    }
    validateToken(token)

    try {
      const encrypted = this.safeStorage.encryptString(token)
      await writeFile(this.tokenPath, encrypted, { mode: 0o600 })
    } catch {
      throw new SecureTokenStoreError('无法保存安全登录状态')
    }
    return { available: true, token: null, reason: null }
  }

  async clearToken(): Promise<SecureTokenSnapshot> {
    try {
      await unlink(this.tokenPath)
    } catch (error) {
      if (!isFileNotFound(error)) {
        throw new SecureTokenStoreError('无法清除安全登录状态')
      }
    }
    return this.safeStorage.isEncryptionAvailable()
      ? { available: true, token: null, reason: null }
      : this.unavailableSnapshot()
  }

  private unavailableSnapshot(): SecureTokenSnapshot {
    return { available: false, token: null, reason: 'secure-storage-unavailable' }
  }
}

function validateToken(token: string): void {
  if (!token || token.length > MAX_TOKEN_LENGTH) {
    throw new SecureTokenStoreError('Token 格式无效')
  }
}

function isFileNotFound(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    (error as { code?: unknown }).code === 'ENOENT'
  )
}

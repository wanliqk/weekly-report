import { randomBytes } from 'node:crypto'
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import type { SafeStorageAdapter } from './secure-token-store'

// A real WeCom cookie jar (see docs/方案设计.md §2.3) is a few dozen small
// name/value pairs; this ceiling only exists to reject an obviously malformed
// or hostile payload before it reaches `safeStorage`/disk.
const MAX_COOKIE_JAR_SERIALIZED_BYTES = 65_536
const SLOT_BYTES = 16
const SLOT_PATTERN = /^[0-9a-f]{32}$/

/**
 * Structured WeCom cookie (`docs/方案设计.md` §2.3): the full jar is kept, not a
 * fixed whitelist of cookie names, because the reference script's fixed name
 * list ("`TOK`、`traceid`、`hashkey`...") is documented as fragile. URL-based
 * filtering of this jar happens in the FastAPI client (WECOM-04) — Electron
 * only stores and returns the jar as-is.
 */
export interface WeComCookie {
  name: string
  value: string
  domain: string
  path: string
  secure: boolean
  httpOnly: boolean
  sameSite: 'unspecified' | 'no_restriction' | 'lax' | 'strict'
  expirationDate: number | null
}

export class WeComCredentialStoreError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'WeComCredentialStoreError'
  }
}

function generateSlot(): string {
  return randomBytes(SLOT_BYTES).toString('hex')
}

/**
 * Encrypts and persists a WeCom cookie jar under a random "credential slot"
 * (`wecom_user_bindings.credential_slot`, WECOM-02) rather than a single
 * fixed path like `SecureTokenStore`'s JWT file, since multiple slots may
 * exist over a binding's lifetime (reconnects) and the slot value itself is
 * the only thing the backend database is allowed to hold (SEC-013 — never
 * the Cookie, never a filesystem path). Slot ids are always generated here
 * from CSPRNG bytes, never derived from a remote id or username
 * (`docs/方案设计.md` §12), which also keeps them safe to use as file names.
 *
 * Mirrors `SecureTokenStore`'s safety properties: `safeStorage` unavailable
 * means the feature is unavailable, never a plaintext fallback; writes use
 * `{ mode: 0o600 }`; a corrupted ciphertext is reported as a typed error
 * (caller should treat it as "sign in again"), never an unhandled exception.
 */
export class WeComCredentialStore {
  constructor(
    private readonly directory: string,
    private readonly safeStorage: SafeStorageAdapter,
    private readonly generateSlotId: () => string = generateSlot
  ) {}

  /** Encrypts `cookieJar` under a freshly generated slot and returns that slot id. */
  async save(cookieJar: WeComCookie[]): Promise<string> {
    if (!this.safeStorage.isEncryptionAvailable()) {
      throw new WeComCredentialStoreError('系统未提供安全存储，无法保存企业微信登录状态')
    }
    validateCookieJar(cookieJar)

    const slot = this.generateSlotId()
    let encrypted: Buffer
    try {
      encrypted = this.safeStorage.encryptString(JSON.stringify(cookieJar))
    } catch {
      throw new WeComCredentialStoreError('无法保存企业微信登录状态')
    }

    try {
      await mkdir(this.directory, { recursive: true, mode: 0o700 })
      await writeFile(this.pathForSlot(slot), encrypted, { mode: 0o600 })
    } catch {
      throw new WeComCredentialStoreError('无法保存企业微信登录状态')
    }
    return slot
  }

  /** Returns the decrypted cookie jar for `slot`, or `null` if no such slot exists. */
  async load(slot: string): Promise<WeComCookie[] | null> {
    validateSlot(slot)
    if (!this.safeStorage.isEncryptionAvailable()) {
      throw new WeComCredentialStoreError('系统未提供安全存储，无法读取企业微信登录状态')
    }

    let encrypted: Buffer
    try {
      encrypted = await readFile(this.pathForSlot(slot))
    } catch (error) {
      if (isFileNotFound(error)) {
        return null
      }
      throw new WeComCredentialStoreError('无法读取企业微信登录状态')
    }

    let cookieJar: unknown
    try {
      const decrypted = this.safeStorage.decryptString(encrypted)
      cookieJar = JSON.parse(decrypted)
    } catch {
      throw new WeComCredentialStoreError('企业微信登录状态已损坏，请重新登录')
    }

    try {
      validateCookieJar(cookieJar)
    } catch {
      throw new WeComCredentialStoreError('企业微信登录状态已损坏，请重新登录')
    }
    return cookieJar
  }

  /** Deletes the credential file for `slot`. Tolerant of an already-missing slot. */
  async delete(slot: string): Promise<void> {
    validateSlot(slot)
    try {
      await rm(this.pathForSlot(slot), { force: true })
    } catch {
      throw new WeComCredentialStoreError('无法清除企业微信登录状态')
    }
  }

  private pathForSlot(slot: string): string {
    return join(this.directory, `${slot}.bin`)
  }
}

function validateSlot(slot: string): void {
  if (!SLOT_PATTERN.test(slot)) {
    throw new WeComCredentialStoreError('凭证槽位无效')
  }
}

function validateCookieJar(value: unknown): asserts value is WeComCookie[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new WeComCredentialStoreError('企业微信登录状态无效')
  }
  if (JSON.stringify(value).length > MAX_COOKIE_JAR_SERIALIZED_BYTES) {
    throw new WeComCredentialStoreError('企业微信登录状态无效')
  }
  for (const entry of value) {
    if (!isWeComCookieShape(entry)) {
      throw new WeComCredentialStoreError('企业微信登录状态无效')
    }
  }
}

function isWeComCookieShape(value: unknown): value is WeComCookie {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const cookie = value as Record<string, unknown>
  return (
    typeof cookie.name === 'string' &&
    typeof cookie.value === 'string' &&
    typeof cookie.domain === 'string' &&
    typeof cookie.path === 'string' &&
    typeof cookie.secure === 'boolean' &&
    typeof cookie.httpOnly === 'boolean' &&
    (cookie.sameSite === 'unspecified' ||
      cookie.sameSite === 'no_restriction' ||
      cookie.sameSite === 'lax' ||
      cookie.sameSite === 'strict') &&
    (cookie.expirationDate === null || typeof cookie.expirationDate === 'number')
  )
}

function isFileNotFound(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    (error as { code?: unknown }).code === 'ENOENT'
  )
}

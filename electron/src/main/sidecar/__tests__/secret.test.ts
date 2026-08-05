import { describe, expect, it } from 'vitest'

import { generateRuntimeSecret } from '../secret'

describe('generateRuntimeSecret', () => {
  it('returns a 64-character hex string (256 bits)', () => {
    const secret = generateRuntimeSecret()

    expect(secret).toMatch(/^[0-9a-f]{64}$/)
  })

  it('returns a different value on each call', () => {
    expect(generateRuntimeSecret()).not.toBe(generateRuntimeSecret())
  })
})

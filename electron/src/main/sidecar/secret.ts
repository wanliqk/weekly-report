import { randomBytes } from 'node:crypto'

export function generateRuntimeSecret(): string {
  return randomBytes(32).toString('hex')
}

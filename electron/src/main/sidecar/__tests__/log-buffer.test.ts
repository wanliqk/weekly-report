import { describe, expect, it } from 'vitest'

import { LOG_BUFFER_MAX_LINES } from '../constants'
import { RedactingLogBuffer } from '../log-buffer'

describe('RedactingLogBuffer', () => {
  it('redacts occurrences of the provided secrets', () => {
    const buffer = new RedactingLogBuffer()

    buffer.append('token=deadbeef leaked', 'deadbeef')

    expect(buffer.getLines()).toEqual(['token=***REDACTED*** leaked'])
  })

  it('redacts every configured secret independently', () => {
    const buffer = new RedactingLogBuffer()

    buffer.append('a=1 b=2', '1', '2')

    expect(buffer.getLines()).toEqual(['a=***REDACTED*** b=***REDACTED***'])
  })

  it('leaves lines untouched when no secret matches', () => {
    const buffer = new RedactingLogBuffer()

    buffer.append('plain log line', 'unrelated-secret')

    expect(buffer.getLines()).toEqual(['plain log line'])
  })

  it('drops the oldest line once the buffer exceeds its bound', () => {
    const buffer = new RedactingLogBuffer()

    for (let index = 0; index < LOG_BUFFER_MAX_LINES + 5; index += 1) {
      buffer.append(`line-${index}`)
    }

    const lines = buffer.getLines()
    expect(lines).toHaveLength(LOG_BUFFER_MAX_LINES)
    expect(lines[0]).toBe('line-5')
    expect(lines[lines.length - 1]).toBe(`line-${LOG_BUFFER_MAX_LINES + 4}`)
  })

  it('clear() empties the buffer', () => {
    const buffer = new RedactingLogBuffer()
    buffer.append('one')

    buffer.clear()

    expect(buffer.getLines()).toEqual([])
  })
})

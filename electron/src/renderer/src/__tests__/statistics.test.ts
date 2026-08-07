import { describe, expect, it } from 'vitest'

import { formatCompletionRate } from '@renderer/utils/statistics'

describe('formatCompletionRate', () => {
  it('renders a null rate (future month) as --', () => {
    expect(formatCompletionRate(null)).toBe('--')
  })

  it('renders a numeric rate with a percent sign', () => {
    expect(formatCompletionRate(71.4)).toBe('71.4%')
  })

  it('renders zero as 0%, not --', () => {
    expect(formatCompletionRate(0)).toBe('0%')
  })
})

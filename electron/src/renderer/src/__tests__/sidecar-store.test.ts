import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSidecarStore } from '@renderer/stores/sidecar'

import type { SidecarStatusSnapshot } from '../../../shared/contracts'

function snapshot(overrides: Partial<SidecarStatusSnapshot> = {}): SidecarStatusSnapshot {
  return {
    state: 'pending',
    reason: null,
    exitCode: null,
    recentLogLines: [],
    updatedAt: 0,
    ...overrides
  }
}

describe('useSidecarStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('init() pulls the current snapshot and applies subsequent pushes', async () => {
    const initial = snapshot({ state: 'pending' })
    let changeListener: ((next: SidecarStatusSnapshot) => void) | undefined

    vi.stubGlobal('window', {
      runtimeBridge: {
        sidecar: {
          getStatus: vi.fn().mockResolvedValue(initial),
          onStatusChange: vi.fn((listener: (next: SidecarStatusSnapshot) => void) => {
            changeListener = listener
            return () => {}
          }),
          retry: vi.fn()
        },
        api: { getConfig: vi.fn() }
      }
    })

    const store = useSidecarStore()
    await store.init()

    expect(store.serviceState).toBe('pending')

    changeListener?.(snapshot({ state: 'ready' }))

    expect(store.serviceState).toBe('ready')
  })

  it('retry() calls the bridge and applies the returned snapshot', async () => {
    const retried = snapshot({ state: 'pending' })
    const retry = vi.fn().mockResolvedValue(retried)

    vi.stubGlobal('window', {
      runtimeBridge: {
        sidecar: {
          getStatus: vi.fn().mockResolvedValue(snapshot({ state: 'failed', reason: 'boom' })),
          onStatusChange: vi.fn(() => () => {}),
          retry
        },
        api: { getConfig: vi.fn() }
      }
    })

    const store = useSidecarStore()
    await store.retry()

    expect(retry).toHaveBeenCalledTimes(1)
    expect(store.snapshot).toEqual(retried)
  })
})

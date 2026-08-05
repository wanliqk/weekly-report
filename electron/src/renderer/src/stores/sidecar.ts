import { defineStore } from 'pinia'

import type { ServiceState, SidecarStatusSnapshot } from '../../../shared/contracts'

function initialSnapshot(): SidecarStatusSnapshot {
  return {
    state: 'pending',
    reason: null,
    exitCode: null,
    recentLogLines: [],
    updatedAt: Date.now()
  }
}

export const useSidecarStore = defineStore('sidecar', {
  state: () => ({
    snapshot: initialSnapshot(),
    unsubscribe: null as (() => void) | null
  }),
  getters: {
    serviceState: (state): ServiceState => state.snapshot.state
  },
  actions: {
    async init(): Promise<void> {
      this.snapshot = await window.runtimeBridge.sidecar.getStatus()
      this.unsubscribe?.()
      this.unsubscribe = window.runtimeBridge.sidecar.onStatusChange((snapshot) => {
        this.snapshot = snapshot
      })
    },
    async retry(): Promise<void> {
      this.snapshot = await window.runtimeBridge.sidecar.retry()
    }
  }
})

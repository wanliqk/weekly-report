import type { RuntimeApiConfig, SidecarStatusSnapshot } from '../shared/contracts'

declare global {
  interface Window {
    readonly desktop: {
      readonly platform: NodeJS.Platform
    }
    readonly runtimeBridge: {
      readonly sidecar: {
        readonly getStatus: () => Promise<SidecarStatusSnapshot>
        readonly onStatusChange: (listener: (snapshot: SidecarStatusSnapshot) => void) => () => void
        readonly retry: () => Promise<SidecarStatusSnapshot>
      }
      readonly api: {
        readonly getConfig: () => Promise<RuntimeApiConfig | null>
      }
    }
  }
}

export {}

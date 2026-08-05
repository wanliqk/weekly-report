import type { ServiceState } from '../../../shared/contracts'

export type { ServiceState }

const messages: Record<ServiceState, string> = {
  pending: '等待桌面进程接入',
  ready: '运行正常',
  failed: '启动失败'
}

export function formatServiceState(state: ServiceState): string {
  return messages[state]
}

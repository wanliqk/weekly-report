import { ElMessage, ElMessageBox } from 'element-plus'

// 全局用户反馈基础设施（FE-01）：页面与 api 层统一经由本模块输出
// 成功/失败/警告提示与确认对话框，禁止页面散落 ElMessage 调用。

export function notifySuccess(message: string): void {
  ElMessage({ type: 'success', message })
}

export function notifyError(message: string): void {
  ElMessage({ type: 'error', message })
}

export function notifyWarning(message: string): void {
  ElMessage({ type: 'warning', message })
}

export function notifyInfo(message: string): void {
  ElMessage({ type: 'info', message })
}

export async function confirmAction(message: string, title = '操作确认'): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
    return true
  } catch {
    return false
  }
}

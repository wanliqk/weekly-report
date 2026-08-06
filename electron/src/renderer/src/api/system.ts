import { requestBinary, requestData } from './client'
import type { BackupCreateData } from '../types/system'

const DEFAULT_FILE_NAME = 'weekly-report-backup.db'

export function createManualBackup(): Promise<BackupCreateData> {
  return requestData({ method: 'POST', url: '/api/v1/system/backups' })
}

export async function downloadManualBackupFile(
  backupId: string
): Promise<{ data: ArrayBuffer; fileName: string }> {
  const { data, fileName } = await requestBinary({
    method: 'GET',
    url: `/api/v1/system/backups/${backupId}/file`
  })
  return { data, fileName: fileName ?? DEFAULT_FILE_NAME }
}

import { writeFile as nodeWriteFile } from 'node:fs/promises'
import { basename } from 'node:path'

import type { BackupSaveResult } from '../../shared/contracts'

// A manual backup is a full-database SQLite snapshot (all users' data, not
// just one report), so it can legitimately be larger than a single report
// export; this ceiling only exists to reject an obviously malformed or
// hostile IPC payload before it reaches the filesystem, not to model a
// realistic V1 database size (attachment-free per-user text data, per
// requirements.md 3.2.3).
const MAX_BACKUP_FILE_BYTES = 100 * 1024 * 1024
const SAFE_FILE_NAME_PATTERN = /^[A-Za-z0-9._-]{1,150}\.db$/

export class BackupFileSaveError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BackupFileSaveError'
  }
}

export interface SaveDialogResult {
  canceled: boolean
  filePath?: string
}

export interface SaveDialogAdapter {
  showSaveDialog: (suggestedName: string) => Promise<SaveDialogResult>
}

export interface FileWriter {
  writeFile: (filePath: string, data: Uint8Array) => Promise<void>
}

const defaultFileWriter: FileWriter = { writeFile: nodeWriteFile }

/**
 * Backs the `backup:save-file` IPC handler. Structurally mirrors
 * `export/file-saver.ts::ExportFileSaver` (same "renderer only ever hands
 * over already-downloaded bytes plus a server-suggested name, never a
 * path" contract) but is kept as its own class with its own `.db` name
 * pattern and size ceiling rather than sharing one, so tightening or
 * loosening either export's or backup's whitelist can never accidentally
 * affect the other.
 */
export class BackupFileSaver {
  constructor(
    private readonly dialogAdapter: SaveDialogAdapter,
    private readonly fileWriter: FileWriter = defaultFileWriter
  ) {}

  async save(suggestedName: unknown, data: unknown): Promise<BackupSaveResult> {
    const validatedName = validateFileName(suggestedName)
    const validatedData = validateFileData(data)

    const { canceled, filePath } = await this.dialogAdapter.showSaveDialog(validatedName)
    if (canceled || !filePath) {
      return { status: 'canceled' }
    }

    try {
      await this.fileWriter.writeFile(filePath, validatedData)
    } catch {
      return { status: 'failed' }
    }
    return { status: 'saved' }
  }
}

function validateFileName(value: unknown): string {
  if (typeof value !== 'string') {
    throw new BackupFileSaveError('rejected invalid backup file name')
  }
  const name = basename(value)
  if (!SAFE_FILE_NAME_PATTERN.test(name)) {
    throw new BackupFileSaveError('rejected invalid backup file name')
  }
  return name
}

function validateFileData(value: unknown): Uint8Array {
  if (
    !(value instanceof Uint8Array) ||
    value.byteLength === 0 ||
    value.byteLength > MAX_BACKUP_FILE_BYTES
  ) {
    throw new BackupFileSaveError('rejected invalid backup file content')
  }
  return value
}

import { writeFile as nodeWriteFile } from 'node:fs/promises'
import { basename } from 'node:path'

import type { ExportSaveResult } from '../../shared/contracts'

// A single generated report export is a handful of columns times a few
// hundred rows at most (requirements.md 4.4 is personal daily-report data,
// not a bulk import); this ceiling only exists to reject an obviously
// malformed or hostile IPC payload before it reaches the filesystem.
const MAX_EXPORT_FILE_BYTES = 25 * 1024 * 1024
const SAFE_FILE_NAME_PATTERN = /^[A-Za-z0-9._-]{1,150}\.xlsx$/

export class ExportFileSaveError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ExportFileSaveError'
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
 * Backs the `export:save-file` IPC handler. The renderer only ever hands
 * over bytes it already downloaded over the (authenticated) REST API plus a
 * server-suggested file name — never a path — so this class's job is to
 * show the native "Save As" dialog and write exactly those bytes to
 * wherever the user picks, without ever handing a filesystem path back to
 * the renderer (modules.md M02: "缺下载保存白名单").
 */
export class ExportFileSaver {
  constructor(
    private readonly dialogAdapter: SaveDialogAdapter,
    private readonly fileWriter: FileWriter = defaultFileWriter
  ) {}

  async save(suggestedName: unknown, data: unknown): Promise<ExportSaveResult> {
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
    throw new ExportFileSaveError('rejected invalid export file name')
  }
  const name = basename(value)
  if (!SAFE_FILE_NAME_PATTERN.test(name)) {
    throw new ExportFileSaveError('rejected invalid export file name')
  }
  return name
}

function validateFileData(value: unknown): Uint8Array {
  if (
    !(value instanceof Uint8Array) ||
    value.byteLength === 0 ||
    value.byteLength > MAX_EXPORT_FILE_BYTES
  ) {
    throw new ExportFileSaveError('rejected invalid export file content')
  }
  return value
}

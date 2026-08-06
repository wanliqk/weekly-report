import { describe, expect, it, vi } from 'vitest'

import { BackupFileSaveError, BackupFileSaver } from '../file-saver'

function saver(overrides?: {
  showSaveDialog?: ReturnType<typeof vi.fn>
  writeFile?: ReturnType<typeof vi.fn>
}): {
  instance: BackupFileSaver
  showSaveDialog: ReturnType<typeof vi.fn>
  writeFile: ReturnType<typeof vi.fn>
} {
  const showSaveDialog =
    overrides?.showSaveDialog ??
    vi.fn().mockResolvedValue({ canceled: false, filePath: 'C:/Users/test/Documents/backup.db' })
  const writeFile = overrides?.writeFile ?? vi.fn().mockResolvedValue(undefined)
  const instance = new BackupFileSaver({ showSaveDialog }, { writeFile })
  return { instance, showSaveDialog, writeFile }
}

describe('BackupFileSaver', () => {
  it('writes the bytes to the path chosen in the save dialog', async () => {
    const data = new Uint8Array([1, 2, 3])
    const { instance, showSaveDialog, writeFile } = saver()

    const result = await instance.save('backup.db', data)

    expect(showSaveDialog).toHaveBeenCalledWith('backup.db')
    expect(writeFile).toHaveBeenCalledWith('C:/Users/test/Documents/backup.db', data)
    expect(result).toEqual({ status: 'saved' })
  })

  it('reports canceled without writing when the dialog is dismissed', async () => {
    const { instance, writeFile } = saver({
      showSaveDialog: vi.fn().mockResolvedValue({ canceled: true })
    })

    const result = await instance.save('backup.db', new Uint8Array([1]))

    expect(writeFile).not.toHaveBeenCalled()
    expect(result).toEqual({ status: 'canceled' })
  })

  it('reports failed when writing throws, without leaking the error', async () => {
    const { instance } = saver({
      writeFile: vi.fn().mockRejectedValue(new Error('disk full'))
    })

    const result = await instance.save('backup.db', new Uint8Array([1]))

    expect(result).toEqual({ status: 'failed' })
  })

  it('strips directory components from the suggested name before it reaches the dialog', async () => {
    const { instance, showSaveDialog } = saver()

    await instance.save('../../evil/backup.db', new Uint8Array([1]))

    expect(showSaveDialog).toHaveBeenCalledWith('backup.db')
  })

  it.each([
    ['missing extension', 'backup'],
    ['wrong extension', 'backup.xlsx'],
    ['path traversal that resolves to an unsafe name', '../../backup#.db'],
    ['not a string', 42],
    ['empty string', '']
  ])('rejects an unsafe suggested name: %s', async (_label, value) => {
    const { instance, showSaveDialog } = saver()

    await expect(instance.save(value, new Uint8Array([1]))).rejects.toThrow(BackupFileSaveError)
    expect(showSaveDialog).not.toHaveBeenCalled()
  })

  it.each([
    ['not a Uint8Array', 'plain string'],
    ['empty buffer', new Uint8Array(0)],
    ['oversized buffer', new Uint8Array(100 * 1024 * 1024 + 1)]
  ])('rejects invalid file content: %s', async (_label, value) => {
    const { instance, showSaveDialog } = saver()

    await expect(instance.save('backup.db', value)).rejects.toThrow(BackupFileSaveError)
    expect(showSaveDialog).not.toHaveBeenCalled()
  })
})

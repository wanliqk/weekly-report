export type ExportStatus = 'processing' | 'succeeded' | 'failed' | 'expired'

export interface ExportFilter {
  date_from?: string
  date_to?: string
  status?: 'archived'
}

export interface ExportCreateRequest {
  report_ids?: string[]
  filter?: ExportFilter
}

export interface ExportJobData {
  id: string
  status: ExportStatus
  record_count: number
  file_name: string | null
  created_at: string
  expires_at: string
}

import adminClient from './adminClient'

export interface MaintenanceJob {
  id: number
  job_name: string
  status: string
  details: Record<string, unknown> | null
  started_at: string
  finished_at: string | null
  duration_seconds: number | null
  result?: Record<string, unknown> | null
  running?: boolean
}

export interface QueuedJobResponse {
  job_id: number
  status: string
  submitted_at: string
}

export interface JobStatusResponse extends MaintenanceJob {
  running: boolean
}

export interface WorkerHealth {
  max_workers: number
  pending_jobs: number[]
  running: number
  completed_result_cache: number
}

export interface BackupSummaryItem {
  file: string
  path: string
  size: number
  createdAt: string
}

export interface BackupSummaryResponse {
  directory: string
  items: BackupSummaryItem[]
}

export interface CleanOrphanPayload {
  apply?: boolean
  delete?: boolean
}

export interface PrunePayload extends CleanOrphanPayload {
  patterns?: string[]
}

export interface VerifyPosterPayload {
  rebuild?: boolean
}

export interface BackupPayload {
  format?: 'plain' | 'custom'
  output?: string
}

export interface MaintenanceScanPayload {
  categories?: string[]
  dry_run?: boolean
  limit?: number
}

export interface MaintenanceScanResponse {
  status?: string
  dry_run?: boolean
  summary?: Record<string, any>
  message?: string
  [key: string]: any
}

export const maintenanceApi = {
  async getDatabaseInfo() {
    const response = await adminClient.get('database/info')
    return response.data
  },

  async cleanOrphans(payload: CleanOrphanPayload = {}): Promise<QueuedJobResponse> {
    const response = await adminClient.post<QueuedJobResponse>('database/clean', payload)
    return response.data
  },

  async pruneTestMedia(payload: PrunePayload = {}): Promise<QueuedJobResponse> {
    const response = await adminClient.post<QueuedJobResponse>('database/prune', payload)
    return response.data
  },

  async verifyPosters(payload: VerifyPosterPayload = {}): Promise<QueuedJobResponse> {
    const response = await adminClient.post<QueuedJobResponse>('database/verify-posters', payload)
    return response.data
  },

  async createBackup(payload: BackupPayload = {}): Promise<QueuedJobResponse> {
    const response = await adminClient.post<QueuedJobResponse>('database/backup', payload)
    return response.data
  },

  async getJobHistory(limit = 20): Promise<{ jobs: MaintenanceJob[] }> {
    const response = await adminClient.get('database/jobs', {
      params: { limit }
    })
    return response.data
  },

  async getJobStatus(jobId: number): Promise<JobStatusResponse> {
    const response = await adminClient.get<JobStatusResponse>(`database/jobs/${jobId}`)
    return response.data
  },

  async cancelJob(jobId: number) {
    const response = await adminClient.delete<{ job_id: number; status: string }>(`database/jobs/${jobId}`)
    return response.data
  },

  async getWorkerHealth(): Promise<WorkerHealth> {
    const response = await adminClient.get<WorkerHealth>('worker/health')
    return response.data
  },

  async listBackups(): Promise<BackupSummaryResponse> {
    const response = await adminClient.get<BackupSummaryResponse>('database/backups')
    return response.data
  },

  async runMaintenanceScan(payload: MaintenanceScanPayload = {}): Promise<MaintenanceScanResponse> {
    const response = await adminClient.post<MaintenanceScanResponse>('media/maintenance-scan', payload)
    return response.data
  }
}

<template>
  <div class="px-6 py-8">
    <header class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">Database Maintenance</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400">Run cleanup, backups, and review maintenance history.</p>
      </div>
      <button
        class="btn-primary"
        :disabled="maintenance.state.isLoading || isActionRunning"
        @click="handleRefresh"
      >
        Refresh
      </button>
    </header>

    <div v-if="isActionRunning" class="mb-4 space-y-3">
      <div class="rounded-md bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 px-4 py-3 text-sm text-blue-800 dark:text-blue-100">
        <div class="flex items-center justify-between">
          <div>
            <span class="font-medium">Working:</span>
            <span class="ml-1">{{ currentActionMessage }}</span>
          </div>
          <button
            class="btn-link text-blue-700 dark:text-blue-200"
            type="button"
            :disabled="!currentJobId"
            @click="handleCancel"
          >
            Cancel
          </button>
        </div>
        <div v-if="currentJobStatus" class="mt-2 text-xs text-blue-700/80 dark:text-blue-200/80">
          <div class="flex items-center gap-2">
            <span class="font-semibold">Job ID:</span>
            <span>{{ currentJobId }}</span>
            <span class="font-semibold">Status:</span>
            <span>{{ currentJobStatus.status.toUpperCase() }}</span>
            <span class="font-semibold" v-if="currentJobStatus.result">Details:</span>
            <pre v-if="currentJobStatus.result" class="bg-blue-100/60 dark:bg-blue-900/40 rounded px-2 py-1 text-[11px] overflow-x-auto">
{{ formattedResult }}
            </pre>
          </div>
        </div>
      </div>
      <div v-if="maintenance.state.workerHealth" class="rounded-md bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 px-4 py-3 text-xs text-gray-700 dark:text-gray-200">
        <div class="font-medium text-gray-800 dark:text-gray-100 mb-1">Worker Health</div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <div>Max workers: <span class="font-semibold">{{ maintenance.state.workerHealth.max_workers }}</span></div>
          <div>Running jobs: <span class="font-semibold">{{ maintenance.state.workerHealth.running }}</span></div>
          <div>Pending IDs: <span class="font-semibold">{{ maintenance.state.workerHealth.pending_jobs.join(', ') || '—' }}</span></div>
          <div>Cached results: <span class="font-semibold">{{ maintenance.state.workerHealth.completed_result_cache }}</span></div>
        </div>
      </div>
    </div>

    <section class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <article class="lg:col-span-2 bg-white dark:bg-gray-800 shadow-sm rounded-lg p-6">
        <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Database Overview</h2>

        <div v-if="maintenance.state.isLoading" class="text-gray-600 dark:text-gray-400">
          Loading database information...
        </div>

        <div v-else-if="maintenance.state.databaseInfo" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Environment</p>
              <p class="text-base text-gray-900 dark:text-gray-100 font-medium">
                {{ maintenance.state.databaseInfo.environment }}
              </p>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Total Size</p>
              <p class="text-base text-gray-900 dark:text-gray-100 font-medium">
                {{ formatBytes(maintenance.state.databaseInfo.total_size as number) }}
              </p>
            </div>
          </div>

          <div>
            <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tables</h3>
            <ul class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <li
                v-for="(count, table) in maintenance.state.databaseInfo.tables as Record<string, number>"
                :key="table"
                class="flex items-center justify-between bg-gray-50 dark:bg-gray-700/40 px-3 py-2 rounded-md"
              >
                <span class="text-sm text-gray-700 dark:text-gray-200">{{ table }}</span>
                <span class="text-sm text-gray-900 dark:text-gray-50 font-semibold">{{ count }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div v-else class="text-gray-600 dark:text-gray-400">
          No database information available. Try refreshing.
        </div>
      </article>

      <aside class="bg-white dark:bg-gray-800 shadow-sm rounded-lg p-6 space-y-4">
        <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Actions</h2>

        <button class="btn-primary w-full" :disabled="isActionRunning || isScanning" @click="runDirectScan">
          {{ isScanning ? 'Scanning Unraid Media...' : 'Scan Unraid Media (18,509 Files)' }}
        </button>
        
        <button class="btn-outline w-full" :disabled="isActionRunning || isScanning" @click="runMediaScan">
          {{ isScanning ? 'Scanning...' : 'Scan Container Media (Limited)' }}
        </button>
        
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runCleanOrphans(false, false)">Dry Run Orphan Check</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runCleanOrphans(true, false)">Mark Orphans Deleted</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runCleanOrphans(true, true)">Delete Orphans</button>

        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runPruneMedia(false, false)">Dry Run Test Prune</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runPruneMedia(true, false)">Mark Test Media Deleted</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runPruneMedia(true, true)">Delete Test Media</button>

        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runVerifyPosters(false)">Verify Poster Data</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runVerifyPosters(true)">Rebuild Missing Posters</button>

        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runBackup('plain')">Create Plain Backup</button>
        <button class="btn-outline w-full" :disabled="isActionRunning" @click="runBackup('custom')">Create Custom Backup</button>
      </aside>
    </section>

    <section class="mt-8 bg-white dark:bg-gray-800 shadow-sm rounded-lg p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100">Maintenance History</h2>
        <button class="btn-secondary" :disabled="maintenance.state.isLoading || isActionRunning" @click="handleRefresh">Refresh History</button>
      </div>

      <div v-if="maintenance.state.jobs.length === 0" class="text-gray-600 dark:text-gray-400">
        No maintenance jobs recorded yet.
      </div>

      <table v-else class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-700/40">
          <tr>
            <th class="px-3 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Job</th>
            <th class="px-3 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Status</th>
            <th class="px-3 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Started</th>
            <th class="px-3 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Duration</th>
            <th class="px-3 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-300">Result Items</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="job in maintenance.state.jobs" :key="job.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/40">
            <td class="px-3 py-2 text-sm text-gray-900 dark:text-gray-100">
              <div class="flex items-center gap-1">
                <span>{{ job.job_name }}</span>
                <span v-if="job.running" class="text-[10px] uppercase tracking-wide text-blue-500">RUNNING</span>
              </div>
            </td>
            <td class="px-3 py-2 text-sm">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                :class="statusClass(job.status)"
              >
                {{ job.status.toUpperCase() }}
              </span>
            </td>
            <td class="px-3 py-2 text-sm text-gray-600 dark:text-gray-300">
              {{ formatDate(job.started_at) }}
            </td>
            <td class="px-3 py-2 text-sm text-gray-600 dark:text-gray-300">
              {{ formatDuration(job.duration_seconds) }}
            </td>
            <td class="px-3 py-2 text-sm text-gray-600 dark:text-gray-300">
              {{ formatResultCount(job.result) }}
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Scan Results Display -->
    <section v-if="scanResults || scanError" class="mt-8 bg-white dark:bg-gray-800 shadow-sm rounded-lg p-6">
      <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Latest Media Scan Results</h2>
      
      <div v-if="scanError" class="rounded-md bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-200 mb-4">
        <strong>Scan Error:</strong> {{ scanError }}
      </div>
      
      <div v-if="scanResults" class="space-y-4">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
            <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{{ scanResults.totalFiles }}</div>
            <div class="text-sm text-blue-800 dark:text-blue-200">Total Files Found</div>
          </div>
          <div class="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
            <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ scanResults.filesAdded }}</div>
            <div class="text-sm text-green-800 dark:text-green-200">Files Added</div>
          </div>
          <div class="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg">
            <div class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{{ scanResults.filesUpdated }}</div>
            <div class="text-sm text-yellow-800 dark:text-yellow-200">Files Updated</div>
          </div>
          <div class="bg-purple-50 dark:bg-purple-900/20 p-3 rounded-lg">
            <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">{{ scanResults.directoriesScanned }}</div>
            <div class="text-sm text-purple-800 dark:text-purple-200">Directories Scanned</div>
          </div>
        </div>
        
        <div class="text-sm text-gray-600 dark:text-gray-400">
          <strong>Completed:</strong> {{ scanResults.timestamp }}
        </div>
        
        <div v-if="Object.keys(scanResults.scanResults).length > 0" class="mt-4">
          <h3 class="text-md font-medium text-gray-900 dark:text-gray-100 mb-2">Scan Details by Category</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <div 
              v-for="(details, category) in scanResults.scanResults" 
              :key="category"
              class="bg-gray-50 dark:bg-gray-700/40 p-3 rounded-md"
            >
              <div class="font-medium text-gray-900 dark:text-gray-100 capitalize">{{ category }}</div>
              <div class="text-sm text-gray-600 dark:text-gray-300">
                {{ details.files_found }} files found, {{ details.files_added }} added
              </div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ details.path }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="maintenance.state.error" class="mt-6">
      <div class="rounded-md bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-200">
        {{ maintenance.state.error }}
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMaintenanceStore } from '@/stores/maintenance'
import { maintenanceApi, type MaintenanceScanPayload, type MaintenanceScanResponse } from '@/api/maintenance'

const router = useRouter()
const authStore = useAuthStore()

if (!authStore.isAdmin) {
  router.replace({ name: 'Home' })
}

const maintenance = useMaintenanceStore()

const isActionRunning = computed(() => Boolean(maintenance.state.activeAction))
const currentActionMessage = computed(() => maintenance.state.actionMessage ?? 'Processing request…')
const currentJobId = computed(() => maintenance.state.currentJobId)
const currentJobStatus = computed(() => maintenance.state.currentJobStatus)
const formattedResult = computed(() => {
  if (!currentJobStatus.value?.result) return ''
  try {
    return JSON.stringify(currentJobStatus.value.result, null, 2)
  } catch (error) {
    return String(currentJobStatus.value.result)
  }
})

async function handleRefresh() {
  await Promise.all([
    maintenance.fetchDatabaseInfo(),
    maintenance.fetchJobs()
  ])
}

async function runCleanOrphans(apply: boolean, deleteRows: boolean) {
  await maintenance.cleanOrphans(apply, deleteRows)
}

async function runPruneMedia(apply: boolean, deleteRows: boolean) {
  await maintenance.pruneTestMedia(apply, deleteRows)
}

async function runVerifyPosters(rebuild: boolean) {
  await maintenance.verifyPosters(rebuild)
}

async function runBackup(format: 'plain' | 'custom') {
  await maintenance.createBackup(format)
}

// Local state for scan results
interface ScanResult {
  timestamp: string
  totalFiles: number
  filesAdded: number
  filesUpdated: number
  directoriesScanned: number
  scanResults: Record<string, any>
  message: string
}

const scanResults = ref<ScanResult | null>(null)
const isScanning = ref(false)
const scanError = ref('')

function mapScanSummary(summary: MaintenanceScanResponse | undefined | null): ScanResult {
  if (!summary) {
    return {
      timestamp: new Date().toLocaleString(),
      totalFiles: 0,
      filesAdded: 0,
      filesUpdated: 0,
      directoriesScanned: 0,
      scanResults: {},
      message: 'No summary returned.'
    }
  }

  const payload = (summary.summary ?? summary) as Record<string, any>
  const totals = payload?.totals ?? {}
  const categories = payload?.categories ?? {}

  const mappedCategories = Object.entries(categories).reduce<Record<string, any>>((acc, [key, value]) => {
    const category = value as Record<string, any>
    acc[key] = {
      files_found: category.files_found ?? 0,
      files_added: category.added ?? 0,
      files_updated: category.updated ?? 0,
      missing: category.missing ?? 0,
      notes: category.notes ?? [],
      path: category.root_path ?? ''
    }
    return acc
  }, {})

  return {
    timestamp: payload?.scanned_at
      ? new Date(payload.scanned_at).toLocaleString()
      : new Date().toLocaleString(),
    totalFiles: totals.files_found ?? 0,
    filesAdded: totals.added ?? 0,
    filesUpdated: totals.updated ?? 0,
    directoriesScanned: totals.categories ?? Object.keys(mappedCategories).length,
    scanResults: mappedCategories,
    message: summary.message ?? payload?.message ?? 'Maintenance scan completed.'
  }
}

async function executeMaintenanceScan(payload: MaintenanceScanPayload, actionDescription: string) {
  try {
    isScanning.value = true
    scanError.value = ''
    scanResults.value = null

    const response = await maintenanceApi.runMaintenanceScan(payload)
    scanResults.value = mapScanSummary(response)

    console.log(`${actionDescription} completed:`, response)

    await maintenance.fetchDatabaseInfo()
    await maintenance.updateWorkerHealth()
  } catch (error) {
    console.error(`${actionDescription} failed:`, error)
    const detail = (error as any)?.response?.data?.detail
    scanError.value = detail ?? (error instanceof Error ? error.message : 'Unknown error')
  } finally {
    isScanning.value = false
  }
}

async function runDirectScan() {
  await executeMaintenanceScan({ dry_run: false }, 'Maintenance scan')
}

async function runMediaScan() {
  await executeMaintenanceScan({ dry_run: true, limit: 500 }, 'Maintenance scan (limited)')
}

async function handleCancel() {
  if (!currentJobId.value) return
  await maintenance.cancelCurrentJob()
}

function formatResultCount(result: Record<string, unknown> | null | undefined) {
  if (!result) return 0
  const details = (result as any).details
  if (Array.isArray(details)) {
    return details.length
  }
  if (details && typeof details === 'object') {
    return Object.keys(details).length
  }
  if (typeof result === 'object') {
    return Object.keys(result).length
  }
  return 1
}

function formatBytes(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exponent = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, exponent)
  return `${value.toFixed(1)} ${units[exponent]}`
}

function formatDate(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function formatDuration(seconds: number | null) {
  if (!seconds) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  return `${minutes}m ${remaining.toFixed(0)}s`
}

function statusClass(status: string) {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
  }
}

onMounted(async () => {
  await handleRefresh()
  await maintenance.updateWorkerHealth()
})

onBeforeUnmount(() => {
  maintenance.stopPolling()
})
</script>

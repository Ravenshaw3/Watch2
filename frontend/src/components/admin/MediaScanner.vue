<template>
  <div class="media-scanner">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
        Media Scanner & Management
      </h2>
      <div class="flex gap-3">
        <button
          @click="refreshStats"
          :disabled="isLoading"
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Scan Status Card -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Scan Status</h3>
      
      <div v-if="scanStatus.is_scanning" class="flex items-center gap-3 mb-4">
        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        <span class="text-blue-600 font-medium">Scan in progress...</span>
      </div>
      
      <div v-else-if="scanStatus.last_scan" class="mb-4">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-3 h-3 rounded-full" :class="getStatusColor(scanStatus.last_scan.status)"></div>
          <span class="font-medium">Last scan: {{ scanStatus.last_scan.status }}</span>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          {{ formatDateTime(scanStatus.last_scan.completed_at) }}
        </p>
      </div>
      
      <div class="flex gap-3">
        <button
          @click="startScan"
          :disabled="scanStatus.is_scanning || isLoading"
          class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {{ scanStatus.is_scanning ? 'Scanning...' : 'Start Full Scan' }}
        </button>
        
        <button
          v-if="scanStatus.is_scanning"
          @click="stopScan"
          class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
          </svg>
          Stop Scan
        </button>
        
        <button
          @click="cleanupOrphaned"
          :disabled="scanStatus.is_scanning || isLoading"
          class="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Cleanup Orphaned
        </button>
      </div>
    </div>

    <!-- Statistics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Files</h4>
        <p class="text-3xl font-bold text-gray-900 dark:text-white">
          {{ stats.total_files?.toLocaleString() || 0 }}
        </p>
      </div>
      
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Recent Additions</h4>
        <p class="text-3xl font-bold text-green-600">
          {{ stats.recent_additions || 0 }}
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400">Last 7 days</p>
      </div>
      
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Duplicate Files</h4>
        <p class="text-3xl font-bold text-orange-600">
          {{ stats.duplicates?.total_duplicate_files || 0 }}
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          {{ stats.duplicates?.duplicate_groups || 0 }} groups
        </p>
      </div>
      
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Categories</h4>
        <p class="text-3xl font-bold text-purple-600">
          {{ Object.keys(stats.by_category || {}).length }}
        </p>
      </div>
    </div>

    <!-- Categories Overview -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Media by Category</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="(count, category) in stats.by_category"
          :key="category"
          class="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
        >
          <span class="font-medium text-gray-900 dark:text-white capitalize">
            {{ category.replace('_', ' ') }}
          </span>
          <span class="text-blue-600 font-bold">{{ count.toLocaleString() }}</span>
        </div>
      </div>
    </div>

    <!-- Storage Usage -->
    <div v-if="stats.storage_by_category" class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Storage Usage</h3>
      
      <div class="space-y-4">
        <div
          v-for="storage in stats.storage_by_category"
          :key="storage.category"
          class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
        >
          <div>
            <h4 class="font-medium text-gray-900 dark:text-white capitalize">
              {{ storage.category.replace('_', ' ') }}
            </h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ storage.file_count }} files • Avg: {{ storage.avg_size_mb }}MB
            </p>
          </div>
          <div class="text-right">
            <p class="text-lg font-bold text-gray-900 dark:text-white">
              {{ storage.total_size_gb }}GB
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- File Formats -->
    <div v-if="stats.file_formats" class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">File Formats</h3>
      
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div
          v-for="format in stats.file_formats"
          :key="format.extension"
          class="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
        >
          <p class="font-mono text-sm text-gray-600 dark:text-gray-400 uppercase">
            .{{ format.extension }}
          </p>
          <p class="text-lg font-bold text-gray-900 dark:text-white">
            {{ format.count }}
          </p>
        </div>
      </div>
    </div>

    <!-- Duplicates Management -->
    <div v-if="duplicates.length > 0" class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Duplicate Files</h3>
        <button
          @click="loadDuplicates"
          :disabled="isLoading"
          class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>
      
      <div class="space-y-4 max-h-96 overflow-y-auto">
        <div
          v-for="duplicate in duplicates"
          :key="duplicate.file_hash"
          class="border border-gray-200 dark:border-gray-600 rounded-lg p-4"
        >
          <div class="flex justify-between items-center mb-2">
            <h4 class="font-medium text-gray-900 dark:text-white">
              {{ duplicate.count }} identical files
            </h4>
            <span class="text-sm text-red-600">
              Wasted: {{ (duplicate.wasted_space / (1024**2)).toFixed(1) }}MB
            </span>
          </div>
          
          <div class="space-y-2">
            <div
              v-for="(file, index) in duplicate.files"
              :key="file.id"
              class="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm"
            >
              <div>
                <p class="font-medium">{{ file.filename }}</p>
                <p class="text-gray-500 dark:text-gray-400">{{ file.filepath }}</p>
              </div>
              <button
                v-if="index > 0"
                @click="deleteFile(file.id)"
                class="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="isLoading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 flex items-center gap-3">
        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        <span class="text-gray-900 dark:text-white">{{ loadingMessage }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Reactive data
const isLoading = ref(false)
const loadingMessage = ref('')
const stats = ref<any>({})
const scanStatus = ref<any>({})
const duplicates = ref<any[]>([])

// Auto-refresh interval
let refreshInterval: NodeJS.Timeout | null = null

onMounted(() => {
  loadData()
  // Auto-refresh every 30 seconds when scanning
  refreshInterval = setInterval(() => {
    if (scanStatus.value.is_scanning) {
      loadScanStatus()
    }
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

async function loadData() {
  await Promise.all([
    loadStats(),
    loadScanStatus(),
    loadDuplicates()
  ])
}

async function loadStats() {
  try {
    const response = await fetch('/api/v1/media-management/stats', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      stats.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to load media stats:', error)
  }
}

async function loadScanStatus() {
  try {
    const response = await fetch('/api/v1/media-management/scan/status', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      scanStatus.value = await response.json()
    }
  } catch (error) {
    console.error('Failed to load scan status:', error)
  }
}

async function loadDuplicates() {
  try {
    const response = await fetch('/api/v1/media-management/duplicates', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      duplicates.value = data.duplicates || []
    }
  } catch (error) {
    console.error('Failed to load duplicates:', error)
  }
}

async function startScan() {
  try {
    isLoading.value = true
    loadingMessage.value = 'Starting media scan...'
    
    const response = await fetch('/api/v1/media-management/scan/start', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        force_rescan: false
      })
    })
    
    if (response.ok) {
      await loadScanStatus()
    } else {
      const error = await response.json()
      alert(`Failed to start scan: ${error.error}`)
    }
  } catch (error) {
    console.error('Failed to start scan:', error)
    alert('Failed to start media scan')
  } finally {
    isLoading.value = false
  }
}

async function stopScan() {
  try {
    const response = await fetch('/api/v1/media-management/scan/stop', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      await loadScanStatus()
    }
  } catch (error) {
    console.error('Failed to stop scan:', error)
  }
}

async function cleanupOrphaned() {
  if (!confirm('Remove database entries for files that no longer exist?')) {
    return
  }
  
  try {
    isLoading.value = true
    loadingMessage.value = 'Cleaning up orphaned entries...'
    
    const response = await fetch('/api/v1/media-management/cleanup/orphaned', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      const result = await response.json()
      alert(`Removed ${result.removed_count} orphaned entries`)
      await loadStats()
    }
  } catch (error) {
    console.error('Failed to cleanup orphaned entries:', error)
    alert('Failed to cleanup orphaned entries')
  } finally {
    isLoading.value = false
  }
}

async function deleteFile(fileId: number) {
  if (!confirm('Delete this file from the database?')) {
    return
  }
  
  try {
    const response = await fetch(`/api/v1/media-management/file/${fileId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    
    if (response.ok) {
      await loadDuplicates()
      await loadStats()
    }
  } catch (error) {
    console.error('Failed to delete file:', error)
  }
}

async function refreshStats() {
  await loadData()
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed': return 'bg-green-500'
    case 'failed': return 'bg-red-500'
    case 'scanning': return 'bg-blue-500'
    default: return 'bg-gray-500'
  }
}

function formatDateTime(dateString: string): string {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString()
}
</script>

<style scoped>
.media-scanner {
  @apply p-6;
}
</style>

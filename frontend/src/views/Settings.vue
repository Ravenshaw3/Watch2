<template>
  <div class="settings-page">
    <div class="container mx-auto px-4 py-8">
      <div class="max-w-4xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
          <p class="text-gray-600">Manage your Watch1 media server configuration</p>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="text-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p class="mt-4 text-gray-600">Loading settings...</p>
        </div>

        <!-- Settings Content -->
        <div v-else class="space-y-8">
          <!-- Media Locations -->
          <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Media Locations</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div v-for="(_, category) in settings.media_locations" :key="category" class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 capitalize">{{ category.replace('_', ' ') }}</label>
                <input
                  v-model="settings.media_locations[category]"
                  type="text"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                  :placeholder="`Path to ${category.replace('_', ' ')}`"
                />
              </div>
            </div>
          </div>

          <!-- UI Settings -->
          <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">User Interface</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Theme</label>
                <select
                  v-model="settings.ui.theme"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="auto">Auto</option>
                </select>
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Default Page Size</label>
                <select
                  v-model="settings.ui.default_page_size"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option :value="6">6 items</option>
                  <option :value="12">12 items</option>
                  <option :value="18">18 items</option>
                  <option :value="24">24 items</option>
                  <option :value="30">30 items</option>
                  <option :value="36">36 items</option>
                </select>
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Default Sort Order</label>
                <select
                  v-model="settings.ui.default_sort_order"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="alphabetical">Alphabetical</option>
                  <option value="date_added">Date Added</option>
                  <option value="date_modified">Date Modified</option>
                  <option value="file_size">File Size</option>
                </select>
              </div>

              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    v-model="settings.ui.show_file_sizes"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Show file sizes</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.ui.show_duration"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Show duration</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.ui.show_ratings"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Show ratings</label>
                </div>
              </div>
            </div>
          </div>

          <!-- Streaming Settings -->
          <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Streaming</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Default Quality</label>
                <select
                  v-model="settings.streaming.default_quality"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="original">Original</option>
                  <option value="1080p">1080p</option>
                  <option value="720p">720p</option>
                  <option value="480p">480p</option>
                </select>
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Max Concurrent Streams</label>
                <input
                  v-model.number="settings.streaming.max_concurrent_streams"
                  type="number"
                  min="1"
                  max="20"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Cache Size (GB)</label>
                <input
                  v-model.number="settings.streaming.cache_size_gb"
                  type="number"
                  min="1"
                  max="100"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    v-model="settings.streaming.enable_transcoding"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable transcoding</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.streaming.cache_enabled"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable caching</label>
                </div>
              </div>
            </div>
          </div>

          <!-- Scanning Settings -->
          <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Media Scanning</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Auto Scan Interval (hours)</label>
                <input
                  v-model.number="settings.scanning.auto_scan_interval_hours"
                  type="number"
                  min="1"
                  max="168"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    v-model="settings.scanning.auto_scan_enabled"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable auto scanning</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.scanning.backup_before_scan"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Backup before scan</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.scanning.skip_other_category"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Skip 'other' category</label>
                </div>
              </div>
            </div>
          </div>

          <!-- Database Settings -->
          <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-900 mb-4">Database</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700">Backup Storage Directory</label>
                <div class="flex flex-col sm:flex-row sm:items-center sm:space-x-3 space-y-3 sm:space-y-0">
                  <input
                    v-model="settings.database.backup_directory"
                    type="text"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Select or enter a backup directory path"
                  />
                  <div class="flex space-x-2">
                    <button
                      type="button"
                      class="px-4 py-2 text-sm font-medium text-primary-600 border border-primary-200 rounded-md hover:bg-primary-50"
                      @click="browseBackupDirectory"
                    >
                      Browse…
                    </button>
                    <button
                      type="button"
                      class="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50"
                      @click="clearBackupDirectory"
                    >
                      Clear
                    </button>
                  </div>
                </div>
                <input
                  ref="backupDirectoryInput"
                  type="file"
                  class="hidden"
                  webkitdirectory
                  directory
                  @change="handleBackupDirectorySelection"
                />
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Backup Interval (hours)</label>
                <input
                  v-model.number="settings.database.backup_interval_hours"
                  type="number"
                  min="1"
                  max="720"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700">Backup Retention (days)</label>
                <input
                  v-model.number="settings.database.backup_retention_days"
                  type="number"
                  min="1"
                  max="365"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div class="space-y-4">
                <div class="flex items-center">
                  <input
                    v-model="settings.database.auto_backup_enabled"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable auto backup</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.database.auto_cleanup_enabled"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable auto cleanup</label>
                </div>
                <div class="flex items-center">
                  <input
                    v-model="settings.database.auto_vacuum_enabled"
                    type="checkbox"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label class="ml-2 block text-sm text-gray-700">Enable auto vacuum</label>
                </div>
              </div>
            </div>

            <div class="mt-6 border-t pt-6">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <h3 class="text-lg font-medium text-gray-900">Backup History</h3>
                  <p class="text-sm text-gray-600">Stored at <span class="font-mono text-xs">{{ settings.database.backup_directory || backupDirectory || 'Not available' }}</span></p>
                </div>
                <button
                  class="px-4 py-2 text-sm font-medium text-primary-600 border border-primary-200 rounded-md hover:bg-primary-50"
                  :disabled="backupsLoading"
                  @click="loadBackups"
                >
                  {{ backupsLoading ? 'Refreshing…' : 'Refresh Backups' }}
                </button>
              </div>

              <div v-if="backupsError" class="text-sm text-red-600">{{ backupsError }}</div>

              <div v-else-if="backupsLoading" class="text-sm text-gray-600">Loading backup history…</div>

              <div v-else-if="backups.length === 0" class="text-sm text-gray-600">No backups found yet.</div>

              <ul v-else class="space-y-3 max-h-64 overflow-y-auto">
                <li
                  v-for="item in backups"
                  :key="item.path"
                  class="border border-gray-200 rounded-md px-3 py-2 text-sm"
                >
                  <div class="flex items-center justify-between">
                    <span class="font-medium">{{ item.file }}</span>
                    <span class="text-gray-500">{{ formatBackupSize(item.size) }}</span>
                  </div>
                  <div class="text-xs text-gray-500">Created {{ formatBackupDate(item.createdAt) }}</div>
                </li>
              </ul>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-end space-x-4 pt-6 border-t">
            <button
              @click="resetSettings"
              class="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              Reset to Defaults
            </button>
            <button
              @click="saveSettings"
              :disabled="saving"
              class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {{ saving ? 'Saving...' : 'Save Settings' }}
            </button>
          </div>
        </div>

        <!-- Success/Error Messages -->
        <div v-if="message" class="mt-4 p-4 rounded-md" :class="messageClass">
          {{ message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import apiClient from '@/api/client'
import { maintenanceApi, type BackupSummaryItem } from '@/api/maintenance'

// Reactive data
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// Default settings structure
const defaultSettings = {
  media_locations: {
    movies: 'T:\\Movies',
    tv_shows: 'T:\\TV Shows',
    music: 'T:\\Music',
    music_videos: 'T:\\Music Videos',
    videos: 'T:\\Videos',
    kids: 'T:\\Kids',
    custom_directories: []
  },
  ui: {
    theme: 'dark',
    default_page_size: 24,
    default_sort_order: 'alphabetical',
    max_page_size: 100,
    show_file_sizes: true,
    show_duration: true,
    show_ratings: true
  },
  streaming: {
    default_quality: 'original',
    enable_transcoding: false,
    transcode_quality: 'medium',
    max_concurrent_streams: 5,
    cache_enabled: true,
    cache_size_gb: 10
  },
  scanning: {
    auto_scan_enabled: false,
    auto_scan_interval_hours: 24,
    backup_before_scan: true,
    skip_other_category: true,
    supported_formats: []
  },
  database: {
    auto_backup_enabled: true,
    backup_directory: '',
    backup_interval_hours: 168,
    backup_retention_days: 30,
    auto_cleanup_enabled: true,
    cleanup_interval_hours: 24,
    auto_vacuum_enabled: true,
    vacuum_interval_hours: 168
  }
}

const settings = ref({ ...defaultSettings })
const backupDirectoryInput = ref<HTMLInputElement | null>(null)
const backupDirectory = ref<string>('')
const backups = ref<BackupSummaryItem[]>([])
const backupsLoading = ref(false)
const backupsError = ref('')

// Computed properties
const messageClass = computed(() => {
  return messageType.value === 'success' 
    ? 'bg-green-50 border border-green-200 text-green-700'
    : 'bg-red-50 border border-red-200 text-red-700'
})

// Methods
declare global {
  interface Window {
    showDirectoryPicker?: () => Promise<{ name?: string; kind?: string }>
  }
}

const loadSettings = async () => {
  try {
    loading.value = true
    const response = await apiClient.get('/settings/')
    const data = response.data || {}
    settings.value = {
      ...defaultSettings,
      ...data,
      media_locations: {
        ...defaultSettings.media_locations,
        ...(data.media_locations || {})
      },
      ui: {
        ...defaultSettings.ui,
        ...(data.ui || {})
      },
      streaming: {
        ...defaultSettings.streaming,
        ...(data.streaming || {})
      },
      scanning: {
        ...defaultSettings.scanning,
        ...(data.scanning || {})
      },
      database: {
        ...defaultSettings.database,
        ...(data.database || {})
      }
    }
    if (settings.value.database?.backup_directory) {
      backupDirectory.value = settings.value.database.backup_directory
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
    showMessage('Failed to load settings', 'error')
  } finally {
    loading.value = false
  }
}

const loadBackups = async () => {
  try {
    backupsLoading.value = true
    backupsError.value = ''
    const { directory, items } = await maintenanceApi.listBackups()
    backupDirectory.value = directory
    backups.value = items
  } catch (error) {
    console.error('Failed to load backups:', error)
    backupsError.value = 'Unable to load backup history.'
  } finally {
    backupsLoading.value = false
  }
}

function formatBackupSize(size: number) {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exponent = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  const value = size / Math.pow(1024, exponent)
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`
}

function formatBackupDate(value: string) {
  return new Date(value).toLocaleString()
}

const saveSettings = async () => {
  try {
    saving.value = true
    await apiClient.put('/settings/', settings.value)
    showMessage('Settings saved successfully!', 'success')
  } catch (error) {
    console.error('Failed to save settings:', error)
    showMessage('Failed to save settings', 'error')
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  if (confirm('Are you sure you want to reset all settings to defaults?')) {
    settings.value = { ...defaultSettings }
    showMessage('Settings reset to defaults', 'success')
  }
}

const showMessage = (msg: string, type: 'success' | 'error') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

const browseBackupDirectory = async () => {
  try {
    if (typeof window.showDirectoryPicker === 'function') {
      const handle = await window.showDirectoryPicker()
      if (handle?.name) {
        settings.value.database.backup_directory = handle.name
        backupDirectory.value = handle.name
      }
      return
    }
  } catch (error) {
    if ((error as DOMException).name !== 'AbortError') {
      console.error('Directory selection failed:', error)
      showMessage('Unable to select directory', 'error')
    }
    return
  }

  if (backupDirectoryInput.value) {
    backupDirectoryInput.value.value = ''
    backupDirectoryInput.value.click()
  }
}

const handleBackupDirectorySelection = (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) {
    return
  }

  const file = files[0] as File & { path?: string; webkitRelativePath?: string }
  let directoryPath = ''

  if (file.path) {
    const normalized = file.path.replace(/\\/g, '/')
    const parts = normalized.split('/')
    parts.pop()
    directoryPath = parts.join('/')
  } else if (file.webkitRelativePath) {
    directoryPath = file.webkitRelativePath.split('/')[0]
  }

  if (directoryPath) {
    settings.value.database.backup_directory = directoryPath
    backupDirectory.value = directoryPath
  }

  input.value = ''
}

const clearBackupDirectory = () => {
  settings.value.database.backup_directory = ''
}

// Lifecycle
onMounted(async () => {
  await loadSettings()
  await loadBackups()
})
</script>

<style scoped>
.settings-page {
  background-color: #f9fafb;
}

.container {
  max-width: 1200px;
}

/* Custom checkbox styling */
input[type="checkbox"]:checked {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

/* Form focus styling */
input:focus, select:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Button hover effects */
button:hover {
  transform: translateY(-1px);
  transition: all 0.2s ease;
}

button:disabled {
  transform: none;
}
</style>

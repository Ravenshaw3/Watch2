import apiClient from './client'
import type {
  MediaFile,
  MediaSearchResponse,
  MediaUploadResponse,
  MediaCategoryInfo,
  MediaScanResult,
  VersionInfo,
  MediaCategory,
  Playlist,
  PlaylistCreate,
  PlaylistUpdate,
  PlaylistItemAdd,
  TVSeriesResponse,
  TVEpisodesResponse,
  PlaylistItem
} from '@/types/media'

type BackendMediaItem = {
  id: string
  title?: string | null
  description?: string | null
  mediaType?: string | null
  sourcePath?: string | null
  status?: string | null
  metadata?: Record<string, any> | null
  durationSeconds?: string | number | null
  createdAt?: string
  updatedAt?: string
}

type BackendPlaylist = {
  id: string
  name: string
  description?: string | null
  isPublic: boolean
  ownerId?: string | null
  createdAt?: string
  updatedAt?: string
}

type BackendPlaylistItem = {
  id: string
  playlistId: string
  mediaItemId: string
  position: string
  addedAt: string
}

type BackendPlaylistWithItems = {
  playlist: BackendPlaylist
  items: { item: BackendPlaylistItem; media?: BackendMediaItem | null }[]
}

const toNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value)
    return Number.isNaN(parsed) ? fallback : parsed
  }
  return fallback
}

const mapMediaItem = (item: BackendMediaItem): MediaFile => {
  const metadata = item.metadata ?? {}

  return {
    id: item.id,
    filename: metadata.filename ?? item.title ?? '',
    original_filename: metadata.originalFilename ?? undefined,
    title: item.title ?? undefined,
    file_path: item.sourcePath ?? '',
    file_size: toNumber(metadata.fileSize),
    mime_type: metadata.mimeType,
    category: (item.mediaType as MediaCategory) ?? MediaCategory.OTHER,
    duration: metadata.duration ?? toNumber(item.durationSeconds),
    width: metadata.width,
    height: metadata.height,
    bitrate: metadata.bitrate,
    codec: metadata.codec,
    container_format: metadata.containerFormat,
    thumbnail_path: metadata.thumbnailPath,
    poster_path: metadata.posterPath,
    artwork: metadata.artwork,
    metadata,
    created_at: item.createdAt ?? new Date().toISOString(),
    uploaded_by: metadata.uploadedBy,
    last_accessed: metadata.lastAccessed,
  }
}

const mapPlaylistItem = (item: BackendPlaylistItem): PlaylistItem => ({
  media_id: item.mediaItemId,
  position: toNumber(item.position),
  added_at: item.addedAt,
})

const mapPlaylist = (playlist: BackendPlaylist, items: PlaylistItem[] = []): Playlist => ({
  id: playlist.id,
  name: playlist.name,
  description: playlist.description ?? undefined,
  items,
  created_by: playlist.ownerId ?? 'system',
  created_at: playlist.createdAt ?? new Date().toISOString(),
  updated_at: playlist.updatedAt ?? new Date().toISOString(),
  is_public: playlist.isPublic,
})

const buildPagination = (page: number, pageSize: number, total: number): MediaSearchResponse => ({
  items: [],
  media: [],
  total,
  page,
  page_size: pageSize,
  categories: {},
})

export const mediaApi = {
  async getMediaFiles(params: {
    page?: number
    page_size?: number
    category?: MediaCategory
    search?: string
    sort_by?: string
    sort_order?: string
  } = {}): Promise<MediaSearchResponse> {
    const page = params.page ?? 1
    const pageSize = params.page_size ?? 25

    const response = await apiClient.get('/media', {
      params: {
        status: params.category,
        search: params.search,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      },
    })

    const items: BackendMediaItem[] = response.data.items ?? []
    const mapped = items.map(mapMediaItem)

    return {
      ...buildPagination(page, pageSize, response.data.total ?? mapped.length),
      items: mapped,
      media: mapped,
      categories: response.data.categories ?? {},
    }
  },

  async getMediaFile(id: string | number): Promise<MediaFile> {
    const response = await apiClient.get(`/media/${id}`)
    return mapMediaItem(response.data)
  },

  async getMediaCategories(): Promise<{ categories: MediaCategoryInfo[] }> {
    const response = await apiClient.get('/media/categories')
    const categories = (response.data.categories ?? []).map((category: any) => ({
      name: category.slug ?? category.name,
      count: category.count ?? 0,
      display_name: category.name ?? category.slug ?? 'Unknown',
    }))

    return { categories }
  },

  async startScan(): Promise<any> {
    const response = await apiClient.post('/media/scan')
    return response.data
  },

  async scanMediaDirectory(directory: string = '/app/media'): Promise<MediaScanResult> {
    const response = await apiClient.post('/media/scan', { directory })
    return response.data
  },

  async getVersion(): Promise<VersionInfo> {
    const response = await apiClient.get('/version')
    return response.data
  },

  async getScanInfo(): Promise<any> {
    const response = await apiClient.get('/media/scan-info')
    return response.data
  },

  async getTVSeries(): Promise<TVSeriesResponse> {
    const response = await apiClient.get('/media/tv-series')
    return response.data
  },

  async getTVSeriesEpisodes(seriesKey: string, season?: number): Promise<TVEpisodesResponse> {
    const params = season ? { season } : {}
    const response = await apiClient.get(`/media/tv-series/${seriesKey}/episodes`, { params })
    return response.data
  },

  async streamMediaFile(id: string): Promise<string> {
    const response = await apiClient.get(`/media/${id}/stream`)
    return response.data.stream_url
  },

  async uploadMediaFile(file: File): Promise<MediaUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/media/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async deleteMediaFile(id: string): Promise<void> {
    await apiClient.delete(`/media/${id}`)
  },

  // Playlist API
  async getPlaylists(): Promise<Playlist[]> {
    const response = await apiClient.get('/playlists')
    const playlists: BackendPlaylist[] = response.data.playlists ?? []
    return playlists.map((playlist) => mapPlaylist(playlist))
  },

  async getPlaylist(id: string): Promise<Playlist> {
    const response = await apiClient.get(`/playlists/${id}`)
    const data: BackendPlaylistWithItems = response.data
    const items = data.items.map((entry) => mapPlaylistItem(entry.item))
    return mapPlaylist(data.playlist, items)
  },

  async createPlaylist(playlistData: PlaylistCreate): Promise<Playlist> {
    const response = await apiClient.post('/playlists', {
      name: playlistData.name,
      description: playlistData.description,
      isPublic: playlistData.is_public,
    })

    return mapPlaylist(response.data)
  },

  async updatePlaylist(id: string, playlistData: PlaylistUpdate): Promise<Playlist> {
    const response = await apiClient.put(`/playlists/${id}`, {
      name: playlistData.name,
      description: playlistData.description,
      isPublic: playlistData.is_public,
    })

    return mapPlaylist(response.data)
  },

  async deletePlaylist(id: string): Promise<void> {
    await apiClient.delete(`/playlists/${id}`)
  },

  async addPlaylistItem(playlistId: string, itemData: PlaylistItemAdd): Promise<void> {
    await apiClient.post(`/playlists/${playlistId}/items`, {
      mediaItemId: itemData.media_id,
      position: itemData.position,
    })
  },

  async removePlaylistItem(playlistId: string, mediaId: string): Promise<void> {
    await apiClient.delete(`/playlists/${playlistId}/items/${mediaId}`)
  },

  async getPlaylistMedia(playlistId: string): Promise<{ media: MediaFile[] }> {
    const response = await apiClient.get(`/playlists/${playlistId}/items`)
    const items = (response.data.items ?? []) as { item: BackendPlaylistItem; media?: BackendMediaItem | null }[]
    const media = items
      .map((entry) => entry.media)
      .filter((mediaItem): mediaItem is BackendMediaItem => Boolean(mediaItem))
      .map(mapMediaItem)

    return { media }
  },
}

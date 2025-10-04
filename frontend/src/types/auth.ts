export interface User {
  id: string
  email: string
  displayName?: string | null
  role: 'admin' | 'editor' | 'viewer'
  createdAt?: string
  updatedAt?: string
  is_superuser?: boolean
}

export interface LoginCredentials {
  email?: string
  username?: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  displayName?: string
}

export interface AuthResponse {
  accessToken: string
  tokenType: string
  user: User & { username?: string; fullName?: string | null }
}

export interface TokenData {
  sub: string
  email: string
  role: User['role']
}

export interface ColorPalette {
  primary: string
  secondary: string
  accent: string
  background: string
  surface: string
  text: string
  text_secondary: string
  border: string
  success: string
  warning: string
  error: string
}

export interface UserPreferences {
  user_id: string
  color_palette: ColorPalette
  theme: string
  layout: string
  items_per_page: number
  auto_scan: boolean
  show_thumbnails: boolean
  created_at: string
  updated_at: string
}

export interface UserPreferencesUpdate {
  color_palette?: ColorPalette
  theme?: string
  layout?: string
  items_per_page?: number
  auto_scan?: boolean
  show_thumbnails?: boolean
}

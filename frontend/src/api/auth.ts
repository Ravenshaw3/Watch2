import apiClient from './client'
import type {
  User,
  LoginCredentials,
  RegisterData,
  AuthResponse,
  UserPreferences,
  UserPreferencesUpdate,
  ColorPalette,
} from '@/types/auth'

type FlaskUserResponse = {
  id: number | string
  email: string
  is_superuser?: boolean
  full_name?: string | null
  username?: string | null
  created_at?: string | null
  updated_at?: string | null
}

type FlaskAuthResponse = {
  access_token: string
  token_type: string
  user: FlaskUserResponse
}

const mapFlaskUser = (payload: FlaskUserResponse): User => {
  return {
    id: String(payload.id),
    email: payload.email,
    displayName: payload.full_name ?? payload.username ?? payload.email,
    role: payload.is_superuser ? 'admin' : 'viewer',
    createdAt: payload.created_at ?? undefined,
    updatedAt: payload.updated_at ?? undefined,
    is_superuser: payload.is_superuser,
  }
}

const mapFlaskAuthResponse = (payload: FlaskAuthResponse): AuthResponse => {
  return {
    accessToken: payload.access_token,
    tokenType: payload.token_type,
    user: mapFlaskUser(payload.user),
  }
}

export const authApi = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<FlaskAuthResponse>('/auth/login/access-token', {
      username: credentials.username ?? credentials.email,
      email: credentials.email,
      password: credentials.password,
    })
    return mapFlaskAuthResponse(response.data)
  },

  // TODO: Replace with Flask registration endpoint when available
  async register(userData: RegisterData): Promise<AuthResponse> {
    const response = await apiClient.post<FlaskAuthResponse>('/auth/register', userData)
    return mapFlaskAuthResponse(response.data)
  },

  async getCurrentUser(): Promise<AuthResponse> {
    const response = await apiClient.get<FlaskUserResponse>('/users/me')
    return {
      accessToken: '',
      tokenType: 'bearer',
      user: mapFlaskUser(response.data),
    }
  },

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response = await apiClient.put('/users/me', userData)
    return response.data
  },

  async getUserPreferences(): Promise<UserPreferences> {
    const response = await apiClient.get('/user/preferences')
    return response.data
  },

  async updateUserPreferences(preferences: UserPreferencesUpdate): Promise<UserPreferences> {
    const response = await apiClient.put('/user/preferences', preferences)
    return response.data
  },

  async getColorPalettes(): Promise<{ palettes: Array<{ name: string; colors: ColorPalette }> }> {
    const response = await apiClient.get('/user/preferences/color-palettes')
    return response.data
  },
}

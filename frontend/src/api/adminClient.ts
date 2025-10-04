import axios, { type AxiosInstance } from 'axios'
import { useAuthStore } from '@/stores/auth'

const adminClient: AxiosInstance = axios.create({
  baseURL: (import.meta as any).env?.VITE_ADMIN_API_URL || '/admin',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

adminClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

adminClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const authStore = useAuthStore()
    if (error.response?.status === 401) {
      await authStore.logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default adminClient

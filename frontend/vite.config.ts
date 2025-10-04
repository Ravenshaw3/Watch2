import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET
  || (process.env.NODE_ENV === 'production' ? 'http://localhost:8000' : 'http://backend:8000')

const adminProxyTarget = process.env.VITE_ADMIN_PROXY_TARGET || 'http://localhost:4000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
      '/admin': {
        target: adminProxyTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  define: {
    __APP_VERSION__: JSON.stringify('3.0.4'),
    __BUILD_DATE__: JSON.stringify(new Date().toISOString().split('T')[0]),
  },
})

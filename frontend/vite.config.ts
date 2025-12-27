import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      // 開發環境下代理 API 請求到後端（保留 /api 前缀）
      '/api': {
        // 在 Docker 環境中使用 backend:8000，本地開發使用 localhost:6000
        target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:6000',
        changeOrigin: true,
        // 不再 rewrite，后端现在使用 /api 前缀
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

  // HTTPS disabled — noVNC iframe requires same protocol (HTTP)
  // Use Chrome flags for mic access on HTTP:
  // chrome://flags/#unsafely-treat-insecure-origin-as-secure
  const httpsConfig = false

  export default defineConfig({
    plugins: [react()],
    build: {
      target: 'esnext',
    },
    optimizeDeps: {
      exclude: ['@novnc/novnc'],
      esbuildOptions: {
        target: 'esnext',
      },
    },
    esbuild: {
      target: 'esnext',
    },
    server: {
      https: httpsConfig,
      proxy: {
        '/ws': {
          target: 'http://localhost:5000',
          ws: true,
          changeOrigin: true,
        },
        '/api': {
          target: 'http://localhost:5000',
          changeOrigin: true,
        },
        '/websockify': {
          target: 'ws://localhost:6080',
          ws: true,
          changeOrigin: true,
        },
      },
    },
  })

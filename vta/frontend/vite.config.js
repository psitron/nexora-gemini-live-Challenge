import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

  // nginx handles HTTPS, proxying, and serving everything on port 443.
  // Vite dev server runs on port 3000 (HTTP) behind nginx.
  // For local dev (no nginx), the proxies below route /ws and /api.

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
      },
    },
  })

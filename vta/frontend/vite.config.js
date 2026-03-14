import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

  // Enable HTTPS if cert files exist (GCE deployment)
  const httpsConfig = fs.existsSync('/etc/ssl/vta/cert.pem')
    ? {
        key: fs.readFileSync('/etc/ssl/vta/key.pem'),
        cert: fs.readFileSync('/etc/ssl/vta/cert.pem'),
      }
    : false

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
      },
    },
  })

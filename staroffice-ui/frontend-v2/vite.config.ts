import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:18791',
      '/ws': {
        target: 'ws://127.0.0.1:18791',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2020',
    cssMinify: 'lightningcss',
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-three':       ['three'],
          'vendor-framer':      ['framer-motion'],
          'vendor-react':       ['react', 'react-dom'],
        },
      },
    },
  },
})

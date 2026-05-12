import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 120000,
        proxyTimeout: 120000,
        // 关键：禁用缓冲以支持 SSE 流
        configure: (proxy, options) => {
          proxy.on('proxyRes', (proxyRes, req, res) => {
            // 确保流式响应不被压缩或缓冲
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              res.setHeader('content-type', 'text/event-stream')
              res.setHeader('cache-control', 'no-cache')
              res.setHeader('connection', 'keep-alive')
            }
          })
        },
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
  },
})

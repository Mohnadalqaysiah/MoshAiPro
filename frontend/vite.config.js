import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Converts render-blocking <link rel="stylesheet"> → async non-blocking load
function deferCSSPlugin() {
  return {
    name: 'defer-css',
    transformIndexHtml(html) {
      return html.replace(
        /<link rel="stylesheet" crossorigin href="([^"]+\.css)">/g,
        (_, href) =>
          `<link rel="preload" as="style" href="${href}" onload="this.rel='stylesheet'">` +
          `<noscript><link rel="stylesheet" href="${href}"></noscript>`
      )
    },
  }
}

export default defineConfig({
  plugins: [react(), deferCSSPlugin()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  preview: {
    host: '0.0.0.0',
    port: process.env.PORT || 3000,
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['recharts'],
          'vendor-icons': ['lucide-react'],
        },
      },
    },
  },
  define: {
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || '')
  }
})

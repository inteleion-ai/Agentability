import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env so VITE_API_URL is available at config time too
  const env = loadEnv(mode, process.cwd(), '')

  // API target — override with:
  //   VITE_API_URL=http://152.67.x.x:8000 npm run dev
  //   VITE_API_URL=http://152.67.x.x:8000 npm run build
  const API_TARGET = env.VITE_API_URL ?? 'http://localhost:8000'

  return {
    plugins: [react()],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },

    // Inject API URL into the build so production bundles know where to call
    define: {
      __API_URL__: JSON.stringify(
        // In production, if VITE_API_URL is set use it; otherwise use '' so
        // the app calls the same origin (works behind nginx reverse-proxy)
        mode === 'production' ? (env.VITE_API_URL ?? '') : ''
      ),
    },

    server: {
      host: '0.0.0.0',   // bind on all interfaces so OCI/VM access works
      port: 3000,
      proxy: {
        '/api': {
          target: API_TARGET,
          changeOrigin: true,
        },
        '/health': {
          target: API_TARGET,
          changeOrigin: true,
        },
        '/metrics': {
          target: API_TARGET,
          changeOrigin: true,
        },
      },
    },

    build: {
      outDir: 'dist',
      sourcemap: true,
    },
  }
})

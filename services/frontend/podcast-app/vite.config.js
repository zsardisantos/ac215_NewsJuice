import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true
    // Removed CORS headers - they blocked Google Cloud Storage audio files
    // VAD now loads locally, so we don't need strict cross-origin policies
  },
  // Only exclude ONNX Runtime from pre-bundling
  // VAD packages need to be pre-bundled to convert CommonJS to ESM
  optimizeDeps: {
    exclude: ['onnxruntime-web']
  },
  // Handle WASM files correctly
  assetsInclude: ['**/*.wasm', '**/*.onnx']
})

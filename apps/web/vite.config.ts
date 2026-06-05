
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    // Fail loudly instead of silently drifting to 5174 when 5173 is busy.
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts'
  }
});

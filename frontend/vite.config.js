import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    allowedHosts: process.env.CODESPACE_NAME
      ? [
          process.env.CODESPACE_NAME +
            '-5173.' +
            (process.env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN || 'app.github.dev'),
        ]
      : [],
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
});

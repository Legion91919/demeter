import { defineConfig } from 'vitest/config';

const api = 'http://localhost:5205';

export default defineConfig({
  server: {
    port: 5285,
    proxy: { '/api': api, '/health': api },
  },
  test: { environment: 'node' },
});

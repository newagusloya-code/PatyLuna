import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '0.0.0.0', // Permite que el teléfono y otros dispositivos en la red Wi-Fi se conecten
    port: 3000,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});

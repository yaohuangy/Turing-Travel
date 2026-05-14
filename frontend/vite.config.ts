import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        timeout: 180000,       // proxy socket timeout (3 min)
        proxyTimeout: 180000,  // proxy read timeout (3 min)
      },
    },
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": { target: apiTarget, changeOrigin: true },
      "/query": { target: apiTarget, changeOrigin: true },
      "/evaluate": { target: apiTarget, changeOrigin: true },
      "/transcribe": { target: apiTarget, changeOrigin: true },
      "/settings": { target: apiTarget, changeOrigin: true },
      "/docs": { target: apiTarget, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});

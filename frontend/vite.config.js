import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev setup: React on :5173, proxying /api to Flask on :5000 so frontend
// code calls fetch("/api/...") with no hard-coded host anywhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});

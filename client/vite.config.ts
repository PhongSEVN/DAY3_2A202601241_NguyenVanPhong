import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [{ find: "@", replacement: path.resolve(__dirname, "./src") }],
  },
  server: {
    port: 5173,
    // Đẩy mọi request /api/* sang backend Flask (src/server.py) => khỏi lo CORS,
    // và API key chỉ nằm ở server chứ không lọt xuống trình duyệt.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

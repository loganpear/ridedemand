import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/user": {
        target: "http://localhost:9000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/user/, ""),
      },
      "/api/availability": {
        target: "http://localhost:9001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/availability/, ""),
      },
      "/api/reservations": {
        target: "http://localhost:9002",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/reservations/, ""),
      },
      "/api/payments": {
        target: "http://localhost:9003",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/payments/, ""),
      },
    },
  },
});

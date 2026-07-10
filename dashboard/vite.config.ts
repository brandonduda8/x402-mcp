import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/stats": "http://localhost:8402",
      "/events": "http://localhost:8402",
      "/ledger": "http://localhost:8402",
      "/doctor": "http://localhost:8402",
      "/probe": "http://localhost:8402",
      "/wallet": "http://localhost:8402",
      "/health": "http://localhost:8402",
      "/seller": "http://localhost:8402",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});

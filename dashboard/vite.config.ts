import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend target: use VITE_API_TARGET env or auto-detect WSL host.
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8402";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/stats": apiTarget,
      "/events": apiTarget,
      "/ledger": apiTarget,
      "/doctor": apiTarget,
      "/probe": apiTarget,
      "/wallet": apiTarget,
      "/health": apiTarget,
      "/seller": apiTarget,
      "/swarm": apiTarget,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});

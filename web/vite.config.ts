/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Vite dev server (port 5173) proxies API calls to FastAPI (port 8000).
// In production FastAPI serves the built files from web/dist on the same origin.
const API_ROUTES = ["/chat", "/stats", "/eval", "/ingest", "/health", "/history"];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(API_ROUTES.map((r) => [r, "http://localhost:8000"])),
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
  },
});

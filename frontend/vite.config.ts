import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  envDir: "..",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    env: {
      VITE_API_BASE_URL: "http://localhost:8000",
      VITE_SSE_BASE_URL: "http://localhost:8000",
      VITE_API_MODE: "mock",
    },
    globals: true,
    setupFiles: "./src/test-setup.ts",
  },
});

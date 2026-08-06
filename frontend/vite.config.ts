import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tsconfigPaths(), tailwindcss()],
  envDir: "..",
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

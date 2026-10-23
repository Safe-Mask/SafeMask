import { defineConfig } from "vite";

// O client e a UI do Tauri: dist/ e embutido no exe (frontendDist do tauri.conf).
export default defineConfig({
  clearScreen: false,
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    target: "safari13",
    outDir: "dist",
  },
});

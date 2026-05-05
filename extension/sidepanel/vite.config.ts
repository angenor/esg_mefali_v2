import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [vue()],
  build: {
    outDir: fileURLToPath(new URL("../dist/sidepanel", import.meta.url)),
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
    cssCodeSplit: false,
    rollupOptions: {
      input: fileURLToPath(new URL("./index.html", import.meta.url)),
      output: {
        entryFileNames: "assets/main.js",
        assetFileNames: "assets/[name][extname]",
        chunkFileNames: "assets/[name].js",
      },
    },
  },
  server: { port: 5174 },
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["**/__tests__/**/*.test.ts"],
  },
});

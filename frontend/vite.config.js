import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo (npm run dev) las llamadas /api se envían al balanceador en :8080
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8080" } },
});

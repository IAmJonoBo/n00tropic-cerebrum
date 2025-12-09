import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  webServer: {
    command: 'pnpm dev -- --host 0.0.0.0 --port 4173',
    port: 4173,
    reuseExistingServer: true,
  },
})

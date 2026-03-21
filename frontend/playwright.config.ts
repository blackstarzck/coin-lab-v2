import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    headless: true,
  },
  webServer: [
    {
      command: "bash -lc 'source .venv/bin/activate && export PYTHONPATH=/Users/chanchan2/Desktop/coin-lab-v2/backend COIN_LAB_APP_ENV=test COIN_LAB_STORE_BACKEND=memory COIN_LAB_ALLOWED_ORIGINS=\"[\\\"http://localhost:4173\\\"]\" && uvicorn app.main:app --host 127.0.0.1 --port 8012'",
      cwd: '/Users/chanchan2/Desktop/coin-lab-v2/backend',
      port: 8012,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host localhost --port 4173',
      cwd: '/Users/chanchan2/Desktop/coin-lab-v2/frontend',
      port: 4173,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 20_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: 'http://localhost:5176',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  reporter: [['list']],
  webServer: {
    command: 'npm run dev -- --port 5176',
    url: 'http://localhost:5176',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8766',
    channel: process.platform === 'win32' ? 'msedge' : undefined,
    viewport: { width: 600, height: 600 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command:
      process.platform === 'win32'
        ? '..\\..\\.venv\\Scripts\\python.exe tests/serve.py'
        : '../../.venv/bin/python tests/serve.py',
    url: 'http://127.0.0.1:8766/health',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});

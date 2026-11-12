import { defineConfig } from '@playwright/test';
import path from 'node:path';

// Explicit config for remote suites: no repository Firefox projects or webServer.
export default defineConfig({
  testDir: path.resolve(process.env.DEV_RUNNER_TEST_DIR || 'tests/e2e'),
  outputDir: path.join(process.env.DEV_RUNNER_ARTIFACTS, 'test-results'),
  workers: 1,
  fullyParallel: false,
  timeout: 60000,
  reporter: [['list'], ['html', {
    outputFolder: path.join(process.env.DEV_RUNNER_ARTIFACTS, 'playwright-report'), open: 'never',
  }]],
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL, headless: false,
    launchOptions: { args: ['--ozone-platform=x11', `--class=${process.env.DEV_RUNNER_CHROME_CLASS}`] },
    trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chrome', use: { browserName: 'chromium', channel: 'chrome' } }],
});

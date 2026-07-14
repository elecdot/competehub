import { defineConfig, devices } from '@playwright/test'

const apiServerCommand =
  '../../scripts/agent-env.sh uv run --project ../api flask --app competehub_api.app:create_e2e_app run --no-reload --host 127.0.0.1 --port 5000'
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_SERVERS === 'true'
const useSystemChrome = process.env.PLAYWRIGHT_USE_SYSTEM_CHROME === 'true'

function runWithBashOnWindows(command: string) {
  if (process.platform !== 'win32') {
    return command
  }
  const gitBash = process.env.GIT_BASH ?? 'C:\\Program Files\\Git\\usr\\bin\\bash.exe'
  const escapedCommand = command.replaceAll("'", "'\\''")
  return `"${gitBash}" -lc '${escapedCommand}'`
}

export default defineConfig({
  testDir: './e2e',
  outputDir: '../../.cache/playwright/test-results',
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { outputFolder: '../../.cache/playwright/report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        ...(useSystemChrome ? { channel: 'chrome' } : {}),
      },
    },
  ],
  webServer: [
    {
      command: runWithBashOnWindows(apiServerCommand),
      url: 'http://127.0.0.1:5000/api/v1/health',
      reuseExistingServer,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer,
      timeout: 120_000,
    },
  ],
})

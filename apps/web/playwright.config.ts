import { defineConfig, devices } from '@playwright/test'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const cacheRoot = resolve(repoRoot, '.cache')
const agentSafeEnvironment = {
  ...process.env,
  AGENT_REPO_ROOT: repoRoot,
  XDG_CACHE_HOME: resolve(cacheRoot, 'xdg-cache'),
  TMPDIR: resolve(cacheRoot, 'tmp'),
  UV_CACHE_DIR: resolve(cacheRoot, 'uv'),
  PIP_CACHE_DIR: resolve(cacheRoot, 'pip'),
  PRE_COMMIT_HOME: resolve(cacheRoot, 'pre-commit'),
  RUFF_CACHE_DIR: resolve(cacheRoot, 'ruff'),
  npm_config_cache: resolve(cacheRoot, 'npm'),
}

const apiServerCommand =
  'uv run --project ../api flask --app competehub_api.app:create_e2e_app run --host 127.0.0.1 --port 5000'
const usesExternalServers = process.env.E2E_EXTERNAL_SERVERS === '1'

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
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 5'] },
    },
  ],
  webServer: usesExternalServers
    ? undefined
    : [
        {
          command: apiServerCommand,
          env: agentSafeEnvironment,
          url: 'http://127.0.0.1:5000/api/v1/health',
          reuseExistingServer: false,
          timeout: 120_000,
        },
        {
          command: 'npm run dev -- --host 127.0.0.1 --port 5173',
          env: agentSafeEnvironment,
          url: 'http://127.0.0.1:5173',
          reuseExistingServer: false,
          timeout: 120_000,
        },
      ],
})

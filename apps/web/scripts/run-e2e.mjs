import { spawn, spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = resolve(appRoot, '../..')
const cacheRoot = resolve(repoRoot, '.cache')
const environment = {
  ...process.env,
  AGENT_REPO_ROOT: repoRoot,
  XDG_CACHE_HOME: resolve(cacheRoot, 'xdg-cache'),
  TMPDIR: resolve(cacheRoot, 'tmp'),
  UV_CACHE_DIR: resolve(cacheRoot, 'uv'),
  PIP_CACHE_DIR: resolve(cacheRoot, 'pip'),
  PRE_COMMIT_HOME: resolve(cacheRoot, 'pre-commit'),
  RUFF_CACHE_DIR: resolve(cacheRoot, 'ruff'),
  npm_config_cache: resolve(cacheRoot, 'npm'),
  E2E_EXTERNAL_SERVERS: '1',
}

const projects = ['desktop-chromium', 'mobile-chromium']
const apiPort = process.env.E2E_API_PORT ?? '5000'

for (const project of projects) {
  await run('uv', [
    'run',
    '--project',
    '../api',
    'flask',
    '--app',
    'competehub_api.app:create_e2e_app',
    'seed-e2e',
    '--reset',
  ])

  const api = start('uv', [
    'run',
    '--project',
    '../api',
    'flask',
    '--app',
    'competehub_api.app:create_e2e_app',
    'run',
    '--host',
    '127.0.0.1',
    '--port',
    apiPort,
  ])
  const web = start(process.execPath, [
    'node_modules/vite/bin/vite.js',
    '--host',
    '127.0.0.1',
    '--port',
    '5173',
  ])

  try {
    await waitFor(`http://127.0.0.1:${apiPort}/api/v1/health`)
    await waitFor('http://127.0.0.1:5173')
    await run(process.execPath, [
      'node_modules/playwright/cli.js',
      'test',
      `--project=${project}`,
    ])
  } finally {
    await terminate(web)
    await terminate(api)
  }
}

function start(command, args) {
  return spawn(command, args, {
    cwd: appRoot,
    env: environment,
    stdio: 'inherit',
  })
}

async function run(command, args) {
  const child = start(command, args)
  const code = await new Promise((resolveExit) => child.on('exit', resolveExit))
  if (code !== 0) {
    throw new Error(`${command} exited with code ${code ?? 'unknown'}.`)
  }
}

async function waitFor(url) {
  const deadline = Date.now() + 120_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.status < 500) {
        return
      }
    } catch {
      // The server is still starting.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250))
  }
  throw new Error(`Timed out waiting for ${url}.`)
}

async function terminate(child) {
  if (child.exitCode !== null || child.pid === undefined) {
    return
  }
  child.kill()
  await waitForExit(child, 2_000)
  if (child.exitCode !== null) {
    return
  }
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore' })
    await waitForExit(child, 2_000)
    return
  }
  child.kill('SIGKILL')
  await waitForExit(child, 2_000)
}

async function waitForExit(child, timeout) {
  if (child.exitCode !== null) {
    return
  }
  await Promise.race([
    new Promise((resolveExit) => child.once('exit', resolveExit)),
    new Promise((resolveDelay) => setTimeout(resolveDelay, timeout)),
  ])
}

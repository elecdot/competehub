import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const [command, ...args] = process.argv.slice(2)

if (!command) {
  throw new Error('Expected a command to run in the E2E environment.')
}

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const cacheRoot = resolve(repoRoot, '.cache')
const result = spawnSync(command, args, {
  cwd: process.cwd(),
  env: {
    ...process.env,
    AGENT_REPO_ROOT: repoRoot,
    XDG_CACHE_HOME: resolve(cacheRoot, 'xdg-cache'),
    TMPDIR: resolve(cacheRoot, 'tmp'),
    UV_CACHE_DIR: resolve(cacheRoot, 'uv'),
    PIP_CACHE_DIR: resolve(cacheRoot, 'pip'),
    PRE_COMMIT_HOME: resolve(cacheRoot, 'pre-commit'),
    RUFF_CACHE_DIR: resolve(cacheRoot, 'ruff'),
    npm_config_cache: resolve(cacheRoot, 'npm'),
  },
  stdio: 'inherit',
})

if (result.error) {
  throw result.error
}

process.exit(result.status ?? 1)

param(
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"

Push-Location $Frontend
try {
  if (-not (Test-Path "node_modules")) {
    npm install
  }
  npm run dev -- --host 0.0.0.0 --port $Port
} finally {
  Pop-Location
}

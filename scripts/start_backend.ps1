param(
  [switch]$Seed
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$PackageDir = Join-Path $Backend ".python_packages"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite:///dev.db" }
$env:FLASK_ENV = if ($env:FLASK_ENV) { $env:FLASK_ENV } else { "development" }
$env:PYTHONPATH = "$PackageDir;$Backend;$env:PYTHONPATH"

Push-Location $Backend
try {
  & $Python -m flask --app run.py init-db
  if ($Seed) {
    Push-Location $Root
    try {
      & $Python (Join-Path $Root "scripts\seed.py")
    } finally {
      Pop-Location
    }
  }
  & $Python -m flask --app run.py run --host 0.0.0.0 --port 5000
} finally {
  Pop-Location
}

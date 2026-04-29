param(
  [switch]$Docker
)

if ($Docker) {
  docker compose up --build
  exit
}

Write-Host "Start backend in one terminal:"
Write-Host "  .\scripts\start_backend.ps1 -Seed"
Write-Host ""
Write-Host "Start frontend in another terminal:"
Write-Host "  .\scripts\start_frontend.ps1"

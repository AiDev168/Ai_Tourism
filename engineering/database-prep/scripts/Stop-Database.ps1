[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $PackageRoot '.env'
if (-not (Test-Path $EnvFile)) { throw 'Database .env is missing.' }

Push-Location $PackageRoot
try {
    & docker compose --project-name ai-tourism-db --env-file $EnvFile stop db
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the AI Tourism database container.' }
    Write-Host 'AI Tourism database stopped. Persistent volume ai_tourism_pgdata was preserved.' -ForegroundColor Green
}
finally {
    Pop-Location
}

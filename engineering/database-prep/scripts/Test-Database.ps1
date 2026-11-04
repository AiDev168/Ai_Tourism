[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $PackageRoot '.env'
if (-not (Test-Path $EnvFile)) { throw 'Database .env is missing. Run Initialize-Database.ps1 first.' }

Push-Location $PackageRoot
try {
    Write-Host "`n========== OFFLINE SEED CONTENT VALIDATION ==========" -ForegroundColor Cyan
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python launcher "py" is required for the offline seed hash/character-count validator.'
    }
    & py -3.13 (Join-Path $PackageRoot 'scripts\Validate-Seed-Data.py')
    if ($LASTEXITCODE -ne 0) { throw 'Offline seed content validation failed.' }

    $health = (& docker inspect --format '{{.State.Health.Status}}' ai-tourism-postgres 2>$null | Out-String).Trim()
    if ($health -ne 'healthy') { throw "ai-tourism-postgres is not healthy (state: '$health'). Start it with Initialize-Database.ps1." }

    function Invoke-PsqlFile([string]$ContainerPath, [string]$MigrationHash = '') {
        $psqlArgs = @('-X', '-v', 'ON_ERROR_STOP=1', '-U', 'ai_tourism_owner', '-d', 'ai_tourism_dev')
        if (-not [string]::IsNullOrWhiteSpace($MigrationHash)) {
            $psqlArgs += @('-v', "migration_hash=$MigrationHash")
        }
        $psqlArgs += @('-f', $ContainerPath)
        & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql @psqlArgs
        if ($LASTEXITCODE -ne 0) { throw "SQL test/seed failed: $ContainerPath" }
    }

    function Get-PsqlScalar([string]$Sql) {
        $result = & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -A -t -U ai_tourism_owner -d ai_tourism_dev -c $Sql
        if ($LASTEXITCODE -ne 0) { throw "Database scalar query failed: $Sql" }
        return (($result | Out-String).Trim())
    }

    Write-Host "`n========== LEGACY SOURCE CHECKSUM ==========" -ForegroundColor Cyan
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
    $LegacySource = Join-Path $ProjectRoot 'database\tourism_points.sql'
    if (-not (Test-Path $LegacySource)) { throw "Original project SQL source is missing: $LegacySource" }
    $legacyHash = (Get-FileHash -LiteralPath $LegacySource -Algorithm SHA256).Hash.ToLowerInvariant()
    $storedLegacyHash = Get-PsqlScalar "SELECT COALESCE((SELECT source_checksum FROM operations.dataset_import_batches WHERE batch_key = 'legacy-user-supplied-destinations-v1'), '');"
    if ($storedLegacyHash -ne $legacyHash) { throw 'Imported legacy-source checksum does not match database import manifest.' }
    Write-Host 'PASS: original project tourism_points.sql checksum matches the imported batch ledger.' -ForegroundColor Green

    Write-Host "`n========== MIGRATION CHECKSUM / SEED IDEMPOTENCY CHECK ==========" -ForegroundColor Cyan
    $migrationSet = @(
        @{ Id = '0001_core_schema'; File = '001_core_schema.sql' },
        @{ Id = '0002_synthetic_knowledge_seed'; File = '002_synthetic_knowledge_seed.sql' },
        @{ Id = '0003_synthetic_e2e_seed'; File = '003_synthetic_e2e_seed.sql' },
        @{ Id = '0004_app_role_grants'; File = '004_app_role_grants.sql' },
        @{ Id = '0005_verified_unesco_destination_seed'; File = '005_verified_unesco_destination_seed.sql' }
    )
    foreach ($migration in $migrationSet) {
        $localPath = Join-Path $PackageRoot (Join-Path 'sql' $migration.File)
        $localHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $databaseHash = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$($migration.Id)'), '');"
        if ($databaseHash -ne $localHash) { throw "Applied migration checksum differs from local file: $($migration.Id)" }
    }

    # Re-run only idempotent seed migrations to prove they do not duplicate data.
    foreach ($seed in @(
        @{ Id = '0002_synthetic_knowledge_seed'; File = '002_synthetic_knowledge_seed.sql'; Path = '/opt/ai-tourism/sql/002_synthetic_knowledge_seed.sql' },
        @{ Id = '0003_synthetic_e2e_seed'; File = '003_synthetic_e2e_seed.sql'; Path = '/opt/ai-tourism/sql/003_synthetic_e2e_seed.sql' },
        @{ Id = '0005_verified_unesco_destination_seed'; File = '005_verified_unesco_destination_seed.sql'; Path = '/opt/ai-tourism/sql/005_verified_unesco_destination_seed.sql' }
    )) {
        $localPath = Join-Path $PackageRoot (Join-Path 'sql' $seed.File)
        $seedHash = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash.ToLowerInvariant()
        Invoke-PsqlFile $seed.Path $seedHash
    }

    Write-Host "`n========== DATABASE ENGINE / EXTENSION VERSIONS ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/000_extension_versions.sql'

    Write-Host "`n========== SCHEMA AND ROW-COUNT INVARIANTS ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/001_schema_seed_invariants.sql'

    Write-Host "`n========== POSTGIS CONTRACT ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/002_geospatial_contract.sql'

    Write-Host "`n========== RAG STORAGE CONTRACT ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/003_rag_storage_contract.sql'

    Write-Host "`n========== FOREIGN KEY / RELATIONSHIP INTEGRITY ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/004_referential_integrity.sql'

    Write-Host "`n========== PRODUCTION PUBLICATION GATES ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/005_production_publication_gate.sql'

    Write-Host "`n========== APPLICATION ROLE SECURITY ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/006_application_role_security.sql'

    Write-Host "`n========== VERIFIED EXTERNAL DATASET / PROVENANCE ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/007_verified_external_dataset.sql'

    Write-Host "`n========== COMPLETE EXPECTED VS ACTUAL ROW COUNTS ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/reports/final_row_counts.sql'

    Write-Host "`nALL DATABASE PRE-CODEX CHECKS PASSED." -ForegroundColor Green
}
finally {
    Pop-Location
}

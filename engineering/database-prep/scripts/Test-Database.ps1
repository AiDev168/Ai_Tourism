[CmdletBinding()]
param(
    [string]$ContainerName = 'ai-tourism-postgres',
    [string]$DatabaseName = 'ai_tourism_dev'
)

$ErrorActionPreference = 'Stop'
$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Import-Module (Join-Path $PSScriptRoot 'Database-Lifecycle.psm1') -Force

Push-Location $PackageRoot
try {
    Write-Host "`n========== OFFLINE SEED CONTENT VALIDATION ==========" -ForegroundColor Cyan
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python launcher "py" is required for the offline seed hash/character-count validator.'
    }
    & py -3.13 (Join-Path $PackageRoot 'scripts\Validate-Seed-Data.py')
    if ($LASTEXITCODE -ne 0) { throw 'Offline seed content validation failed.' }

    $containerState = (& docker inspect --format '{{.State.Status}}' $ContainerName 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $containerState -ne 'running') {
        throw "Database container '$ContainerName' is not running (state: '$containerState'). Start the intended database before validation."
    }
    & docker exec $ContainerName pg_isready -U ai_tourism_owner -d $DatabaseName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Database '$DatabaseName' in '$ContainerName' is not accepting connections." }

    function Invoke-PsqlFile([string]$ContainerPath, [string]$MigrationHash = '') {
        $psqlArgs = @('-X', '-v', 'ON_ERROR_STOP=1', '-U', 'ai_tourism_owner', '-d', $DatabaseName)
        if (-not [string]::IsNullOrWhiteSpace($MigrationHash)) {
            $psqlArgs += @('-v', "migration_hash=$MigrationHash")
        }
        $psqlArgs += @('-f', $ContainerPath)
        & docker exec $ContainerName psql @psqlArgs
        if ($LASTEXITCODE -ne 0) { throw "SQL test/seed failed: $ContainerPath" }
    }

    function Get-PsqlScalar([string]$Sql) {
        $result = & docker exec $ContainerName psql -X -A -t -U ai_tourism_owner -d $DatabaseName -c $Sql
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

    Write-Host "`n========== DATABASE STATE / MIGRATION CHECKSUM PREFLIGHT ==========" -ForegroundColor Cyan
    $appliedIds = @((Get-PsqlScalar "SELECT COALESCE(string_agg(migration_id, ',' ORDER BY migration_id), '') FROM system.schema_migrations;").Split(',', [StringSplitOptions]::RemoveEmptyEntries))
    $state = Resolve-DatabaseLifecycleState -AppliedMigrationIds $appliedIds
    $databaseState = "$($state.Name) / $($state.ExpectedRows) rows"
    $expectedMigrations = $state.MigrationIds

    $migrationSet = @(
        @{ Id = '0000_legacy_tourism_points_baseline'; Path = $LegacySource },
        @{ Id = '0001_core_schema'; Path = (Join-Path $PackageRoot 'sql\001_core_schema.sql') },
        @{ Id = '0002_synthetic_knowledge_seed'; Path = (Join-Path $PackageRoot 'sql\002_synthetic_knowledge_seed.sql') },
        @{ Id = '0003_synthetic_e2e_seed'; Path = (Join-Path $PackageRoot 'sql\003_synthetic_e2e_seed.sql') },
        @{ Id = '0004_app_role_grants'; Path = (Join-Path $PackageRoot 'sql\004_app_role_grants.sql') },
        @{ Id = '0005_verified_unesco_destination_seed'; Path = (Join-Path $PackageRoot 'sql\005_verified_unesco_destination_seed.sql') },
        @{ Id = '0006_verified_unesco_destination_seed_batch2'; Path = (Join-Path $PackageRoot 'sql\006_verified_unesco_destination_seed_batch2.sql') },
        @{ Id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'; Path = (Join-Path $PackageRoot 'sql\007_shiraz_dalahoo_wikipedia_dataset_v1.sql') },
        @{ Id = '0008_authentication_foundation'; Path = (Join-Path $PackageRoot 'sql\008_authentication_foundation.sql') }
    ) | Where-Object { $_.Id -in $expectedMigrations }
    foreach ($migration in $migrationSet) {
        $localHash = (Get-FileHash -LiteralPath $migration.Path -Algorithm SHA256).Hash.ToLowerInvariant()
        $databaseHash = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$($migration.Id)'), '');"
        if ($databaseHash -ne $localHash) { throw "Applied migration checksum differs from local file: $($migration.Id)" }
    }

    Write-Host "PASS: exact migration ledger/checksums identify $databaseState." -ForegroundColor Green

    # The report derives its exact 419/695-row manifest from the ledger and
    # fails closed on partial imports, count drift, or the wrong row state.
    Write-Host "`n========== EXACT STATE ROW-COUNT PREFLIGHT ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/reports/final_row_counts.sql'

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

    Write-Host "`n========== SECOND VERIFIED EXTERNAL DATASET BATCH ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/tests/008_verified_external_dataset_batch2.sql'

    if ($state.IncludesShiraz) {
        Write-Host "`n========== SHIRAZ DATASET INTEGRATION / PUBLICATION GATE ==========" -ForegroundColor Cyan
        Invoke-PsqlFile '/opt/ai-tourism/sql/tests/009_shiraz_dataset_integration.sql'
    }
    else {
        Write-Host 'PASS: Migration 0007 is absent; Shiraz migration/test were not applied or executed.' -ForegroundColor Green
    }

    if ($state.IncludesAuthentication) {
        Write-Host "`n========== AUTHENTICATION FOUNDATION / DATABASE ACCESS ==========" -ForegroundColor Cyan
        Invoke-PsqlFile '/opt/ai-tourism/sql/tests/010_authentication_foundation.sql'
    }

    Write-Host "`n========== COMPLETE EXPECTED VS ACTUAL ROW COUNTS ==========" -ForegroundColor Cyan
    Invoke-PsqlFile '/opt/ai-tourism/sql/reports/final_row_counts.sql'

    Write-Host "`nALL DATABASE PRE-CODEX CHECKS PASSED." -ForegroundColor Green
}
finally {
    Pop-Location
}

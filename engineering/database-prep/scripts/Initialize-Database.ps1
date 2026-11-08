[CmdletBinding()]
param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path,
    [switch]$ApplyPendingMigrationsToExistingDatabase,
    [switch]$ApplyAuthenticationMigrationToExistingDatabase,
    [switch]$ApplyTravelerCoreMigrationToExistingDatabase
)

$ErrorActionPreference = 'Stop'
$LifecycleModule = Join-Path $PSScriptRoot 'Database-Lifecycle.psm1'
Import-Module $LifecycleModule -Force
$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$LegacySource = Join-Path $ProjectRoot 'database\tourism_points.sql'
$LegacyDir = Join-Path $PackageRoot 'legacy'
$LegacyCopy = Join-Path $LegacyDir 'tourism_points.sql'
$EnvFile = Join-Path $PackageRoot '.env'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI was not found. Start Docker Desktop and verify: docker version'
}
if (-not (Test-Path $LegacySource)) {
    throw "Existing project dataset SQL was not found: $LegacySource"
}

# Refuse to adopt unrelated resources that happen to use this package's fixed names.
# Read Docker's JSON output instead of using a Go template with a quoted label key.
# The latter is not passed reliably to docker.exe by Windows PowerShell 5.1.
function Get-DockerComposeProjectLabel {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('container', 'volume')]
        [string]$ResourceType,

        [Parameter(Mandatory = $true)]
        [string]$ResourceName
    )

    # Windows PowerShell 5.1 converts native stderr into PowerShell error
    # records. With this script's Stop preference, even the expected
    # "No such container/volume" response can terminate the script.
    # Temporarily use Continue and capture both streams so we can inspect the
    # native exit code and distinguish an absent resource from a real CLI error.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $inspectOutput = @(& docker $ResourceType inspect $ResourceName 2>&1)
        $inspectExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($inspectExitCode -ne 0) {
        $diagnostic = ($inspectOutput | Out-String).Trim()
        if ($diagnostic -match '(?i)(no such container|no such volume|no such object|container .* not found|volume .* not found)') {
            return $null
        }
        throw "Docker inspect failed for $ResourceType '$ResourceName' (exit $inspectExitCode): $diagnostic"
    }

    # A successful inspect must contain JSON only. Do not silently treat
    # malformed output as an absent resource.
    try {
        $inspectJson = ($inspectOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        $inspectObjects = @($inspectJson | ConvertFrom-Json -ErrorAction Stop)
    }
    catch {
        throw "Docker returned invalid JSON while inspecting $ResourceType '$ResourceName': $($_.Exception.Message)"
    }

    if ($inspectObjects.Count -ne 1) {
        throw "Expected one inspect result for $ResourceType '$ResourceName'; received $($inspectObjects.Count)."
    }

    if ($ResourceType -eq 'container') {
        $labels = $inspectObjects[0].Config.Labels
    }
    else {
        $labels = $inspectObjects[0].Labels
    }

    if ($null -eq $labels) {
        return ''
    }

    $labelProperty = $labels.PSObject.Properties['com.docker.compose.project']
    if ($null -eq $labelProperty) {
        return ''
    }

    return [string]$labelProperty.Value
}

$existingContainerProject = Get-DockerComposeProjectLabel -ResourceType 'container' -ResourceName 'ai-tourism-postgres'
if ($null -ne $existingContainerProject -and $existingContainerProject -ne 'ai-tourism-db') {
    throw 'A container named ai-tourism-postgres exists but is not owned by Compose project ai-tourism-db. It will not be modified.'
}

$existingVolumeProject = Get-DockerComposeProjectLabel -ResourceType 'volume' -ResourceName 'ai_tourism_pgdata'
if ($null -ne $existingVolumeProject -and $existingVolumeProject -ne 'ai-tourism-db') {
    throw 'A volume named ai_tourism_pgdata exists but is not owned by Compose project ai-tourism-db. It will not be reused or modified.'
}

New-Item -ItemType Directory -Force -Path $LegacyDir | Out-Null
Copy-Item -LiteralPath $LegacySource -Destination $LegacyCopy -Force

# Create local-only admin/application credentials. Never print or commit them.
$existingLines = if (Test-Path $EnvFile) { Get-Content -LiteralPath $EnvFile } else { @() }
$envValues = @{}
foreach ($line in $existingLines) {
    if ($line -match '^([A-Z_]+)=(.*)$') { $envValues[$matches[1]] = $matches[2] }
}

function New-RandomSecret {
    $bytes = New-Object byte[] 36
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
}

if (-not $envValues.ContainsKey('POSTGRES_PASSWORD') -or $envValues['POSTGRES_PASSWORD'].Length -lt 24) {
    $envValues['POSTGRES_PASSWORD'] = New-RandomSecret
}
if (-not $envValues.ContainsKey('POSTGRES_APP_PASSWORD') -or $envValues['POSTGRES_APP_PASSWORD'].Length -lt 24) {
    $envValues['POSTGRES_APP_PASSWORD'] = New-RandomSecret
}
$envValues['POSTGRES_DB'] = 'ai_tourism_dev'
$envValues['POSTGRES_USER'] = 'ai_tourism_owner'
$envValues['POSTGRES_APP_USER'] = 'ai_tourism_app'
$envContent = @(
    "POSTGRES_DB=$($envValues['POSTGRES_DB'])",
    "POSTGRES_USER=$($envValues['POSTGRES_USER'])",
    "POSTGRES_PASSWORD=$($envValues['POSTGRES_PASSWORD'])",
    "POSTGRES_APP_USER=$($envValues['POSTGRES_APP_USER'])",
    "POSTGRES_APP_PASSWORD=$($envValues['POSTGRES_APP_PASSWORD'])"
) -join "`n"
Set-Content -LiteralPath $EnvFile -Value $envContent -Encoding ASCII
Write-Host 'Local-only database owner and least-privilege app credentials are present in .env.' -ForegroundColor Green

Push-Location $PackageRoot
try {
    Write-Host "`n========== BUILD AND START ISOLATED DATABASE ==========" -ForegroundColor Cyan
    & docker compose --project-name ai-tourism-db --env-file $EnvFile up -d --build db
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed.' }

    $health = ''
    for ($i = 0; $i -lt 120; $i++) {
        $health = (& docker inspect --format '{{.State.Health.Status}}' ai-tourism-postgres 2>$null | Out-String).Trim()
        if ($health -eq 'healthy') { break }
        if ($health -eq 'unhealthy') { throw 'Database container healthcheck reported unhealthy. Inspect: docker logs ai-tourism-postgres' }
        Start-Sleep -Seconds 2
    }
    if ($health -ne 'healthy') { throw "Database did not become healthy. Last health state: '$health'. Inspect: docker logs ai-tourism-postgres" }

    function Invoke-PsqlFile([string]$ContainerPath) {
        & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d ai_tourism_dev -f $ContainerPath
        if ($LASTEXITCODE -ne 0) { throw "SQL execution failed: $ContainerPath" }
    }

    function Get-PsqlScalar([string]$Sql) {
        $result = & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -A -t -U ai_tourism_owner -d ai_tourism_dev -c $Sql
        if ($LASTEXITCODE -ne 0) { throw "Database scalar query failed: $Sql" }
        return (($result | Out-String).Trim())
    }

    # Classify existing data before bootstrap, seed, checksum-ledger, or import
    # writes. Only a truly empty database, exact 0006, or exact 0007 is accepted.
    $ledgerExists = Get-PsqlScalar "SELECT CASE WHEN to_regclass('system.schema_migrations') IS NULL THEN 'no' ELSE 'yes' END;"
    $projectTableCount = Get-PsqlScalar "SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname IN ('identity','conversation','travel','knowledge','recommendation','integration','operations','system');"
    $projectSchemaCount = Get-PsqlScalar "SELECT COUNT(*) FROM pg_catalog.pg_namespace WHERE nspname IN ('identity','conversation','travel','knowledge','recommendation','integration','operations','system');"
    $projectExtensionCount = Get-PsqlScalar "SELECT COUNT(*) FROM pg_catalog.pg_extension WHERE extname IN ('postgis','vector');"
    $databaseState = ''
    if ($ledgerExists -eq 'no' -and $projectTableCount -eq '0' -and $projectSchemaCount -eq '0' -and $projectExtensionCount -eq '0') {
        $databaseState = 'fresh'
    }
    elseif ($ledgerExists -ne 'yes') {
        throw "Database has partial or unexpected state without a migration ledger ($projectSchemaCount project schemas, $projectTableCount project tables, $projectExtensionCount project extensions). Initialization stopped without applying migrations. Inspect this database manually."
    }
    else {
        $appliedIds = @((Get-PsqlScalar "SELECT COALESCE(string_agg(migration_id, ',' ORDER BY migration_id), '') FROM system.schema_migrations;").Split(',', [StringSplitOptions]::RemoveEmptyEntries))
        $state = Resolve-DatabaseLifecycleState -AppliedMigrationIds $appliedIds
        $databaseState = $state.Name
        $expectedMigrations = $state.MigrationIds

        $migrationFiles = @(
            @{ Id = '0000_legacy_tourism_points_baseline'; Path = $LegacySource },
            @{ Id = '0001_core_schema'; Path = (Join-Path $PackageRoot 'sql\001_core_schema.sql') },
            @{ Id = '0002_synthetic_knowledge_seed'; Path = (Join-Path $PackageRoot 'sql\002_synthetic_knowledge_seed.sql') },
            @{ Id = '0003_synthetic_e2e_seed'; Path = (Join-Path $PackageRoot 'sql\003_synthetic_e2e_seed.sql') },
            @{ Id = '0004_app_role_grants'; Path = (Join-Path $PackageRoot 'sql\004_app_role_grants.sql') },
            @{ Id = '0005_verified_unesco_destination_seed'; Path = (Join-Path $PackageRoot 'sql\005_verified_unesco_destination_seed.sql') },
            @{ Id = '0006_verified_unesco_destination_seed_batch2'; Path = (Join-Path $PackageRoot 'sql\006_verified_unesco_destination_seed_batch2.sql') },
            @{ Id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'; Path = (Join-Path $PackageRoot 'sql\007_shiraz_dalahoo_wikipedia_dataset_v1.sql') },
            @{ Id = '0008_authentication_foundation'; Path = (Join-Path $PackageRoot 'sql\008_authentication_foundation.sql') },
            @{ Id = '0009_traveler_core'; Path = (Join-Path $PackageRoot 'sql\009_traveler_core.sql') }
        ) | Where-Object { $_.Id -in $expectedMigrations }
        foreach ($migration in $migrationFiles) {
            $localHash = (Get-FileHash -LiteralPath $migration.Path -Algorithm SHA256).Hash.ToLowerInvariant()
            $databaseHash = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$($migration.Id)'), '');"
            if ($databaseHash -ne $localHash) {
                throw "Migration checksum mismatch for $($migration.Id). Initialization stopped without applying pending migrations."
            }
        }

        Write-Host "Validating existing database state $databaseState without applying migrations..." -ForegroundColor Cyan
        Invoke-PsqlFile '/opt/ai-tourism/sql/reports/final_row_counts.sql'
        $initializationAction = Resolve-DatabaseInitializationAction -State $databaseState `
            -ApplyPendingMigrationsToExistingDatabase:$ApplyPendingMigrationsToExistingDatabase `
            -ApplyAuthenticationMigrationToExistingDatabase:$ApplyAuthenticationMigrationToExistingDatabase `
            -ApplyTravelerCoreMigrationToExistingDatabase:$ApplyTravelerCoreMigrationToExistingDatabase

        if ($initializationAction -eq 'already-integrated') {
            Write-Host 'Database already has the validated 0007 / 695-row state. No changes are needed.' -ForegroundColor Green
            return
        }
        if ($initializationAction -eq 'already-authenticated') {
            Write-Host "Database state $databaseState already includes the validated authentication migration. No changes are needed." -ForegroundColor Green
            return
        }
        if ($initializationAction -eq 'already-traveler-core') {
            Write-Host "Database state $databaseState already includes the validated traveler-core migration. No changes are needed." -ForegroundColor Green
            return
        }
        if ($initializationAction -eq 'apply-pending-0007') {
            Write-Host 'Explicit opt-in received for applying pending Migration 0007 to the validated 0006 database.' -ForegroundColor Yellow
        }
    }

    function Register-Migration([string]$MigrationId, [string]$Hash) {
        $sql = "INSERT INTO system.schema_migrations (migration_id, sha256) VALUES ('$MigrationId', '$Hash') ON CONFLICT (migration_id) DO NOTHING;"
        & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d ai_tourism_dev -c $sql
        if ($LASTEXITCODE -ne 0) { throw "Could not register migration $MigrationId" }
    }

    if ($databaseState -eq 'fresh') {
        Write-Host "`n========== EXTENSIONS AND MIGRATION CONTROL ==========" -ForegroundColor Cyan
        & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -v ON_ERROR_STOP=1 -v "app_user=$($envValues['POSTGRES_APP_USER'])" -v "app_password=$($envValues['POSTGRES_APP_PASSWORD'])" -U ai_tourism_owner -d ai_tourism_dev -f '/opt/ai-tourism/sql/000_bootstrap.sql'
        if ($LASTEXITCODE -ne 0) { throw 'Bootstrap failed: extensions, migration ledger or application role.' }
    }
    else {
        Write-Host 'Existing database state validated; bootstrap and legacy seed are skipped.' -ForegroundColor DarkGreen
    }

    $legacyId = '0000_legacy_tourism_points_baseline'
    $legacyHash = (Get-FileHash -LiteralPath $LegacySource -Algorithm SHA256).Hash.ToLowerInvariant()
    $legacyApplied = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$legacyId'), '');"

    if ([string]::IsNullOrWhiteSpace($legacyApplied)) {
        $legacyTableExists = Get-PsqlScalar "SELECT CASE WHEN to_regclass('knowledge.destinations') IS NULL THEN 'no' ELSE 'yes' END;"
        if ($legacyTableExists -ne 'no') {
            throw 'A knowledge.destinations table exists but the package has no baseline migration marker. Stop for manual review; no database was reset.'
        }
        Write-Host 'Applying the existing 15-record project dataset as unverified legacy input...' -ForegroundColor Yellow
        Invoke-PsqlFile '/opt/ai-tourism/legacy/tourism_points.sql'
        $legacyCount = Get-PsqlScalar 'SELECT COUNT(*) FROM knowledge.destinations;'
        if ($legacyCount -ne '15') { throw "Expected 15 legacy destinations from the current SQL file; found $legacyCount. Review the import before continuing." }
        Register-Migration $legacyId $legacyHash
    }
    elseif ($legacyApplied -ne $legacyHash) {
        throw 'The legacy tourism_points.sql checksum differs from the already-applied baseline. Use a new migration; do not edit an applied baseline in place.'
    }
    else {
        Write-Host 'Legacy baseline already applied with matching checksum.' -ForegroundColor DarkGreen
    }

    $migrations = @(
        @{ Id = '0001_core_schema'; File = '001_core_schema.sql'; Path = '/opt/ai-tourism/sql/001_core_schema.sql' },
        @{ Id = '0002_synthetic_knowledge_seed'; File = '002_synthetic_knowledge_seed.sql'; Path = '/opt/ai-tourism/sql/002_synthetic_knowledge_seed.sql' },
        @{ Id = '0003_synthetic_e2e_seed'; File = '003_synthetic_e2e_seed.sql'; Path = '/opt/ai-tourism/sql/003_synthetic_e2e_seed.sql' },
        @{ Id = '0004_app_role_grants'; File = '004_app_role_grants.sql'; Path = '/opt/ai-tourism/sql/004_app_role_grants.sql' },
        @{ Id = '0005_verified_unesco_destination_seed'; File = '005_verified_unesco_destination_seed.sql'; Path = '/opt/ai-tourism/sql/005_verified_unesco_destination_seed.sql' },
        @{ Id = '0006_verified_unesco_destination_seed_batch2'; File = '006_verified_unesco_destination_seed_batch2.sql'; Path = '/opt/ai-tourism/sql/006_verified_unesco_destination_seed_batch2.sql' },
        @{ Id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'; File = '007_shiraz_dalahoo_wikipedia_dataset_v1.sql'; Path = '/opt/ai-tourism/sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql' },
        @{ Id = '0008_authentication_foundation'; File = '008_authentication_foundation.sql'; Path = '/opt/ai-tourism/sql/008_authentication_foundation.sql' },
        @{ Id = '0009_traveler_core'; File = '009_traveler_core.sql'; Path = '/opt/ai-tourism/sql/009_traveler_core.sql' }
    )

    if ($databaseState -ne 'fresh') {
        if ($initializationAction -eq 'apply-pending-0007') {
            $migrations = @($migrations | Where-Object { $_.Id -eq '0007_shiraz_dalahoo_wikipedia_dataset_v1' })
        }
        elseif ($initializationAction -like 'apply-auth-0008-*') {
            $migrations = @($migrations | Where-Object { $_.Id -eq '0008_authentication_foundation' })
        }
        elseif ($initializationAction -like 'apply-traveler-0009-*') {
            $migrations = @($migrations | Where-Object { $_.Id -eq '0009_traveler_core' })
        }
        else {
            throw "Unexpected migration action '$initializationAction'; stopped before writes."
        }
    }

    foreach ($migration in $migrations) {
        $filePath = Join-Path $PackageRoot (Join-Path 'sql' $migration.File)
        $hash = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        $appliedHash = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$($migration.Id)'), '');"

        if ([string]::IsNullOrWhiteSpace($appliedHash)) {
            Write-Host "Applying $($migration.Id)..." -ForegroundColor Yellow
            $migrationArgs = @('-X', '-v', 'ON_ERROR_STOP=1', '-v', "migration_hash=$hash", '-U', 'ai_tourism_owner', '-d', 'ai_tourism_dev')
            if ($migration.Id -eq '0004_app_role_grants') {
                $migrationArgs += @('-v', "app_user=$($envValues['POSTGRES_APP_USER'])")
            }
            $migrationArgs += @('-f', $migration.Path)
            & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql @migrationArgs
            if ($LASTEXITCODE -ne 0) { throw "Migration execution failed: $($migration.Id)" }
            $verifiedMigrationHash = Get-PsqlScalar "SELECT COALESCE((SELECT sha256 FROM system.schema_migrations WHERE migration_id = '$($migration.Id)'), '');"
            if ($verifiedMigrationHash -ne $hash) { throw "Migration ledger verification failed: $($migration.Id)" }
        }
        elseif ($appliedHash -ne $hash) {
            throw "Checksum mismatch for already-applied migration $($migration.Id). Do not modify applied migrations; add a new migration instead."
        }
        else {
            Write-Host "Already applied: $($migration.Id)" -ForegroundColor DarkGreen
        }
    }

    # The import ledger is created by migration 001 and seeded by migration 002.
    # Record the source SQL checksum only after that table and batch row exist.
    if ($databaseState -eq 'fresh') {
        $batchChecksumSql = "UPDATE operations.dataset_import_batches SET source_checksum = '$legacyHash' WHERE batch_key = 'legacy-user-supplied-destinations-v1';"
        & docker compose --project-name ai-tourism-db --env-file $EnvFile exec -T db psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d ai_tourism_dev -c $batchChecksumSql
        if ($LASTEXITCODE -ne 0) { throw 'Could not store the original tourism SQL checksum in the dataset import ledger.' }
    }
    $storedBatchChecksum = Get-PsqlScalar "SELECT COALESCE((SELECT source_checksum FROM operations.dataset_import_batches WHERE batch_key = 'legacy-user-supplied-destinations-v1'), '');"
    if ($storedBatchChecksum -ne $legacyHash) { throw 'Legacy import ledger checksum verification failed.' }

    Write-Host "`nDatabase is ready: localhost:55433 / ai_tourism_dev" -ForegroundColor Green
    Write-Host 'Next: run scripts\Test-Database.ps1'
}
finally {
    Pop-Location
}
